import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import numpy as np
import pandas as pd
import json
import re


@keras.utils.register_keras_serializable()
class MultiHeadSelfAttentionLayer(layers.Layer):

    def __init__(self, embed_dim, num_heads=4, dropout_rate=0.1, **kwargs):
        super().__init__(**kwargs)
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.dropout_rate = dropout_rate

        assert embed_dim % num_heads == 0
        self.head_dim = embed_dim // num_heads

        self.query_dense = layers.Dense(embed_dim, use_bias=False)
        self.key_dense = layers.Dense(embed_dim, use_bias=False)
        self.value_dense = layers.Dense(embed_dim, use_bias=False)
        self.output_dense = layers.Dense(embed_dim)

        self.dropout = layers.Dropout(dropout_rate)
        self.layer_norm = layers.LayerNormalization(epsilon=1e-6)

    def build(self, input_shape):
        self.query_dense.build(input_shape)
        self.key_dense.build(input_shape)
        self.value_dense.build(input_shape)
        self.output_dense.build(input_shape)
        self.layer_norm.build(input_shape)
        super().build(input_shape)

    def split_heads(self, x, batch_size):
        x = tf.reshape(x, (batch_size, -1, self.num_heads, self.head_dim))
        return tf.transpose(x, perm=[0, 2, 1, 3])

    def call(self, inputs, training=False):
        batch_size = tf.shape(inputs)[0]

        q = self.split_heads(self.query_dense(inputs), batch_size)
        k = self.split_heads(self.key_dense(inputs), batch_size)
        v = self.split_heads(self.value_dense(inputs), batch_size)

        scale = tf.math.sqrt(tf.cast(self.head_dim, tf.float32))
        scores = tf.matmul(q, k, transpose_b=True) / scale
        weights = tf.nn.softmax(scores, axis=-1)
        weights = self.dropout(weights, training=training)

        context = tf.matmul(weights, v)
        context = tf.transpose(context, perm=[0, 2, 1, 3])
        context = tf.reshape(context, (batch_size, -1, self.embed_dim))

        output = self.output_dense(context)
        output = self.layer_norm(inputs + output)

        return output

    def get_config(self):
        config = super().get_config()
        config.update({
            "embed_dim": self.embed_dim,
            "num_heads": self.num_heads,
            "dropout_rate": self.dropout_rate
        })
        return config


@keras.utils.register_keras_serializable()
class FocalLoss(keras.losses.Loss):

    def __init__(self, gamma=2.0, alpha=0.25, name='focal_loss', **kwargs):
        super().__init__(name=name, **kwargs)
        self.gamma = gamma
        self.alpha = alpha

    def call(self, y_true, y_pred):
        y_true = tf.cast(y_true, tf.int32)
        y_true_one_hot = tf.one_hot(y_true, depth=tf.shape(y_pred)[-1])

        y_pred = tf.clip_by_value(y_pred, 1e-7, 1.0 - 1e-7)

        ce_loss = -y_true_one_hot * tf.math.log(y_pred)

        pt = tf.reduce_sum(y_true_one_hot * y_pred, axis=-1, keepdims=True)
        focal_weight = tf.pow(1.0 - pt, self.gamma)

        loss = self.alpha * focal_weight * ce_loss
        return tf.reduce_mean(tf.reduce_sum(loss, axis=-1))

    def get_config(self):
        config = super().get_config()
        config.update({
            "gamma": self.gamma,
            "alpha": self.alpha
        })
        return config


class ProductCategoryPredictor:

    def __init__(self, model_path, metadata_path, custom_objects=None):
        print("Memuat model...")

        self.model = keras.models.load_model(
            model_path,
            custom_objects=custom_objects or {}
        )

        with open(metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)

        self.classes = self.metadata['classes']

        print("Model berhasil dimuat!")
        print(f"Jumlah kelas: {len(self.classes)}")

    def clean_text(self, text):
        if not isinstance(text, str):
            return ""
        text = text.lower().strip()
        text = re.sub(r'\b\d+\s*(pcs|ml|gr|kg|ltr|cm|mm|mg|g|l|oz)\b', '', text)
        text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def predict(self, product_name, top_k=3, threshold=0.1):
        cleaned = self.clean_text(product_name)
        input_tensor = tf.constant([cleaned], dtype=tf.string)

        probs = self.model.predict(input_tensor, verbose=0)[0]

        pred_idx = np.argmax(probs)
        pred_class = self.classes[pred_idx]
        pred_conf = float(probs[pred_idx])

        top_k_idx = np.argsort(probs)[::-1][:top_k]

        top_k_preds = []
        for i, idx in enumerate(top_k_idx):
            conf = float(probs[idx])
            if conf >= threshold:
                top_k_preds.append({
                    "rank": i + 1,
                    "category": self.classes[idx],
                    "confidence": conf,
                    "percentage": f"{conf*100:.2f}%"
                })

        return {
            "product_name": product_name,
            "predicted_category": pred_class,
            "confidence_pct": f"{pred_conf*100:.2f}%",
            "top_k_predictions": top_k_preds
        }
    
    def predict_batch(self, product_names, batch_size=64):
        cleaned_names = [self.clean_text(name) for name in product_names]
        
        all_probs = []
        for i in range(0, len(cleaned_names), batch_size):
            batch = cleaned_names[i:i + batch_size]
            batch_tensor = tf.constant(batch, dtype=tf.string)
            batch_probs = self.model.predict(batch_tensor, verbose=0)
            all_probs.append(batch_probs)
        
        all_probs = np.vstack(all_probs)
        pred_indices = np.argmax(all_probs, axis=1)
        pred_classes = [self.classes[i] for i in pred_indices]
        pred_confidences = np.max(all_probs, axis=1)
        
        return pd.DataFrame({
            'product_name': product_names,
            'predicted_category': pred_classes,
            'confidence_pct': [f"{c*100:.2f}%" for c in pred_confidences]
        })