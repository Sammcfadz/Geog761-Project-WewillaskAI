import geoai

directory = "Training Data"
geoai.train_segmentation_model(
    images_dir=f"{directory}/nasa_patches_split",
    labels_dir=f"{directory}/nasa_masks_split",
    output_dir=f"{directory}/unet_models",
    architecture="unet",
    encoder_name="resnet34",
    encoder_weights="imagenet",
    num_channels=9,
    num_classes=2,  # background and water
    batch_size=32,
    num_epochs=3,  # training for 3 epochs to save time, in practice you should train for more epochs
    learning_rate=0.001,
    val_split=0.2,
    verbose=True,
)

# Performance statistics
geoai.plot_performance_metrics(
    history_path=f"{directory}/unet_models/training_history.pth",
    figsize=(15, 5),
    verbose=True,
)