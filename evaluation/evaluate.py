"""
evaluation/evaluate.py
Evaluates trained models and generates evaluation plots:
- confusion_matrix.png
- feature_importance.png
- model_comparison.png
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
import joblib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless execution
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix

EVAL_DIR = os.path.dirname(__file__)


def run_evaluation():
    test_data_path = os.path.join(EVAL_DIR, "test_data.pkl")
    if not os.path.exists(test_data_path):
        raise FileNotFoundError(f"{test_data_path} not found. Run train.py first.")

    bundle = joblib.load(test_data_path)
    X_test = bundle["X_test"]
    y_test = bundle["y_test"]
    models = bundle["models"]
    best_name = bundle["best_model_name"]
    best_model = models[best_name]

    print(f"Evaluating best model: {best_name} on {len(X_test)} test instances...")

    # 1. Confusion Matrix Plot
    y_pred = best_model.predict(X_test)
    cm = confusion_matrix(y_test, y_pred)

    plt.figure(figsize=(6, 5))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["Incompatible / Warning (0)", "Compatible (1)"],
        yticklabels=["Incompatible / Warning (0)", "Compatible (1)"]
    )
    plt.title(f"Confusion Matrix — {best_name}")
    plt.xlabel("Predicted Label")
    plt.ylabel("Ground Truth Label")
    plt.tight_layout()
    cm_path = os.path.join(EVAL_DIR, "confusion_matrix.png")
    plt.savefig(cm_path, dpi=300)
    plt.close()
    print(f"Saved confusion matrix plot to {cm_path}")

    # 2. Feature Importance Plot (for Random Forest / Decision Tree)
    if hasattr(best_model, "feature_importances_"):
        features = list(X_test.columns)
        importances = best_model.feature_importances_
        fi_df = pd.DataFrame({
            "Feature": [f.replace("_compatible", "").capitalize() for f in features],
            "Importance": importances
        }).sort_values(by="Importance", ascending=False)

        plt.figure(figsize=(7, 4.5))
        sns.barplot(data=fi_df, x="Importance", y="Feature", hue="Feature", palette="viridis", legend=False)
        plt.title(f"Feature Importance — {best_name}")
        plt.xlabel("Gini Importance Score")
        plt.ylabel("Electrical Compatibility Feature")
        plt.tight_layout()
        fi_path = os.path.join(EVAL_DIR, "feature_importance.png")
        plt.savefig(fi_path, dpi=300)
        plt.close()
        print(f"Saved feature importance plot to {fi_path}")

    # 3. Model Comparison Plot
    report_path = os.path.join(EVAL_DIR, "training_report.json")
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        comp_data = []
        for m_name, metrics in report["models_evaluated"].items():
            comp_data.append({
                "Model": m_name,
                "Accuracy": metrics["test_accuracy"],
                "Precision": metrics["test_precision"],
                "Recall": metrics["test_recall"],
                "F1-Score": metrics["test_f1"]
            })

        df_comp = pd.DataFrame(comp_data)
        df_melted = df_comp.melt(id_vars="Model", var_name="Metric", value_name="Score")

        plt.figure(figsize=(8, 5))
        sns.barplot(data=df_melted, x="Metric", y="Score", hue="Model", palette="Set2")
        plt.ylim(0.85, 1.02)
        plt.title("Model Performance Comparison on Test Set")
        plt.ylabel("Score")
        plt.legend(loc="lower right")
        plt.tight_layout()
        comp_plot_path = os.path.join(EVAL_DIR, "model_comparison.png")
        plt.savefig(comp_plot_path, dpi=300)
        plt.close()
        print(f"Saved model comparison plot to {comp_plot_path}")

    print("All evaluation plots generated successfully!")


if __name__ == "__main__":
    run_evaluation()
