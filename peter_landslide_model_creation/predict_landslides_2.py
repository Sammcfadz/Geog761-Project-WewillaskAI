import geoai

model_path = "Trained Model/unet_models/final_model.pth"
input_path = "Training Data/nasa_patches_original/s1s2_combined_1.tif"
masks_path = "Training Data/nasa_masks_original/landslide_mask_1.tif"
output_path = "Training Data/predictions/landslide_1.tif"
NUM_IMAGES = 2000

geoai.semantic_segmentation(
    input_path=input_path,
    output_path=output_path,
    model_path=model_path,
    architecture="unet",
    encoder_name="resnet34",
    num_channels=9,
    num_classes=2,
)

# gdf = geoai.orthogonalize(masks_path, output_path, epsilon=2)
# import geopandas as gpd

# gdf = gpd.read_file(output_path)
# print(f"Number of polygons: {len(gdf)}")
# print(gdf.head())


# pred_raster = geoai.predict_segmentation_model(
#     model_dir=model_path,
#     input_raster=input_path,
#     output_dir=output_path,
# )

# 2. Visualize the segmentation results
# geoai.view_raster_interactive(pred_raster, basemap="satellite")