import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Read the CSV file
directory = "peter_landslide_model_creation"
df = pd.read_csv(f"{directory}/model_metrics.csv")

print("DataFrame contents:")
print(df)
print("\nUnique model names:")
print(df.iloc[:, 0].unique())

# ============= XGBoost Plot =============
# Try different possible names for XGBoost
xgb_names = ["xg boost", "xgboost", "XGBoost", "XG Boost"]
xgb_data = None

for name in xgb_names:
    xgb_data = df[df.iloc[:, 0] == name].copy()
    if len(xgb_data) > 0:
        print(f"\nFound XGBoost data with name: '{name}'")
        break

if xgb_data is None or len(xgb_data) == 0:
    print("Warning: XGBoost data not found in CSV")
else:
    # Extract data
    xgb_classes = xgb_data.iloc[:, 1].values
    xgb_precision = xgb_data["precision"].values
    xgb_recall = xgb_data["recall"].values
    xgb_f1 = xgb_data["f1-score"].values

    # Set up plotting
    metrics = ["Precision", "Recall", "F1-Score"]
    x = np.arange(len(metrics))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create bars for each class
    bars1 = ax.bar(
        x - width / 2,
        [xgb_precision[0], xgb_recall[0], xgb_f1[0]],
        width,
        label="Class 0",
        alpha=0.8,
        color="#3498db",
    )
    bars2 = ax.bar(
        x + width / 2,
        [xgb_precision[1], xgb_recall[1], xgb_f1[1]],
        width,
        label="Class 1",
        alpha=0.8,
        color="#e74c3c",
    )

    # Customize plot
    ax.set_ylabel("Score", fontsize=12)
    ax.set_xlabel("Metrics", fontsize=12)
    ax.set_title("XGBoost Performance by Class", fontsize=14, pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=11)
    ax.legend(fontsize=11)
    ax.set_ylim([0, 1.1])
    ax.grid(axis="y", alpha=0.3, linestyle="--")

    # Add value labels
    def add_labels(bars):
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{height:.3f}",
                ha="center",
                va="bottom",
                fontsize=10,
            )

    add_labels(bars1)
    add_labels(bars2)

    # Add reference line
    ax.axhline(y=0.5, color="gray", linestyle=":", linewidth=1, alpha=0.5)

    plt.tight_layout()
    save_path = f"{directory}/xgboost_detailed_comparison.png"
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    print(f"XGBoost plot saved to: {save_path}")
    plt.show()


# ============= Random Forest Plot =============
# Try different possible names for Random Forest
rf_names = ["Random Forests", "Random Forest", "random forest", "RF"]
rf_data = None

for name in rf_names:
    rf_data = df[df.iloc[:, 0] == name].copy()
    if len(rf_data) > 0:
        print(f"\nFound Random Forest data with name: '{name}'")
        break

if rf_data is None or len(rf_data) == 0:
    print("Warning: Random Forest data not found in CSV")
else:
    # Extract data
    rf_classes = rf_data.iloc[:, 1].values
    rf_precision = rf_data["precision"].values
    rf_recall = rf_data["recall"].values
    rf_f1 = rf_data["f1-score"].values

    # Set up plotting
    metrics = ["Precision", "Recall", "F1-Score"]
    x = np.arange(len(metrics))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create bars for each class
    bars1 = ax.bar(
        x - width / 2,
        [rf_precision[0], rf_recall[0], rf_f1[0]],
        width,
        label="Class 0",
        alpha=0.8,
        color="#2ecc71",
    )
    bars2 = ax.bar(
        x + width / 2,
        [rf_precision[1], rf_recall[1], rf_f1[1]],
        width,
        label="Class 1",
        alpha=0.8,
        color="#f39c12",
    )

    # Customize plot
    ax.set_ylabel("Score", fontsize=12)
    ax.set_xlabel("Metrics", fontsize=12)
    ax.set_title("Random Forest Performance by Class", fontsize=14, pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=11)
    ax.legend(fontsize=11)
    ax.set_ylim([0, 1.1])
    ax.grid(axis="y", alpha=0.3, linestyle="--")

    # Add value labels
    def add_labels(bars):
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{height:.3f}",
                ha="center",
                va="bottom",
                fontsize=10,
            )

    add_labels(bars1)
    add_labels(bars2)

    # Add reference line
    ax.axhline(y=0.5, color="gray", linestyle=":", linewidth=1, alpha=0.5)

    plt.tight_layout()
    save_path = f"{directory}/random_forest_detailed_comparison.png"
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    print(f"Random Forest plot saved to: {save_path}")
    plt.show()
