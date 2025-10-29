import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Read the CSV file
directory = "peter_landslide_model_creation"
df = pd.read_csv(f"{directory}/model_metrics.csv")  # Adjust path as needed

# Display the dataframe to verify
print(df)

# Set up the data for plotting
models = df.iloc[:, 0].values  # First column (model names)
classes = df.iloc[:, 1].values  # Second column (class labels)
precision = df["precision"].values
recall = df["recall"].values
f1_score = df["f1-score"].values

# Create labels for each bar
labels = [f"{model}\nClass {cls}" for model, cls in zip(models, classes)]

# Set up bar positions
x = np.arange(len(labels))
width = 0.25  # Width of each bar

# Create the figure and axis
fig, ax = plt.subplots(figsize=(14, 7))

# Create bars for each metric
bars1 = ax.bar(
    x - width, precision, width, label="Precision", alpha=0.8, color="#3498db"
)
bars2 = ax.bar(x, recall, width, label="Recall", alpha=0.8, color="#2ecc71")
bars3 = ax.bar(x + width, f1_score, width, label="F1-Score", alpha=0.8, color="#e74c3c")

# Customize the plot
ax.set_ylabel("Score", fontsize=12, fontweight="bold")
ax.set_xlabel("Model and Class", fontsize=12, fontweight="bold")
ax.set_title(
    "Model Performance Comparison: Precision, Recall, and F1-Score",
    fontsize=14,
    fontweight="bold",
    pad=20,
)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=10)
ax.legend(fontsize=11, loc="upper right")
ax.set_ylim([0, 1.1])  # Set y-axis from 0 to 1.1
ax.grid(axis="y", alpha=0.3, linestyle="--")


# Add value labels on top of bars
def add_value_labels(bars):
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:.3f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )


add_value_labels(bars1)
add_value_labels(bars2)
add_value_labels(bars3)

# Add a horizontal line at y=0.5 for reference
ax.axhline(y=0.5, color="gray", linestyle=":", linewidth=1, alpha=0.5)

plt.tight_layout()

# Save the figure
save_path = f"{directory}/model_comparison_barchart.png"
plt.savefig(save_path, dpi=300, bbox_inches="tight")
print(f"\nChart saved to: {save_path}")

plt.show()
