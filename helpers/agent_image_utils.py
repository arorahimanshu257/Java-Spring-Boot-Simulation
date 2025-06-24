#!/usr/bin/env python3
"""
agent_image_utils.py

Provides helper methods to process base64 encoded images found
within a user inputs dictionary by saving them to temporary files, and also
a method to clean up these temporary files.
"""

import os
import base64
import tempfile
import logging
from fastapi import HTTPException

logger = logging.getLogger("agent_image_utils.py")

def save_data_uri_to_temp_file(data_uri: str) -> str:
    """
    Saves a data URI (base64 encoded image data) to a temporary file and returns the file path.
    Args:
        data_uri (str): The data URI string containing the base64 encoded image.

    Returns:
        str: The file path to the saved temporary image file.

    Raises:
        HTTPException: If there is a problem decoding or writing the image data.
    """
    try:
        # If the data URI contains a header (like "data:image/xxx;base64,"), remove it.
        if 'base64,' in data_uri:
            base64_data = data_uri.split('base64,')[1]
        else:
            base64_data = data_uri

        # Decode the base64 data.
        image_data = base64.b64decode(base64_data)

        # Create a temporary file to write the image data.
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', mode='w+b', delete=False)
        temp_file.write(image_data)
        temp_file.close()

        return temp_file.name

    except Exception as e:
        logger.error("Error saving data URI to temporary file: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

def save_temp_images_with_rewrite_inputs(user_inputs: dict) -> tuple:
    """
    Scans the user_inputs dictionary for keys that represent images—determined
    by trimming curly braces from the key and checking if it starts with 'image' (case-insensitive).
    For any such key containing a base64 encoded image string, saves the image to a temporary file,
    then replaces the original image data in the dictionary with the file path.

    Args:
        user_inputs (dict): The original dictionary of user inputs, possibly containing
            base64 encoded image strings.

    Returns:
        tuple: A tuple containing:
          - A list of temporary file paths for the images that were saved.
          - The updated user_inputs dictionary with image data replaced by file paths.
    """
    temporary_images = []

    # Convert the dictionary items into a list to safely modify the dictionary as iterating.
    for key, value in list(user_inputs.items()):
        if isinstance(value, str):
            # Clean the key by removing curly braces and extra whitespace.
            cleaned_key = key.strip("{}").strip().lower()
            # Check if the key seems to correspond to an image (e.g., "image", "image_1", etc.).
            if cleaned_key.startswith("image"):
                try:
                    temp_path = save_data_uri_to_temp_file(value)
                    # Replace the original base64 string with the temporary file path.
                    user_inputs[key] = temp_path
                    temporary_images.append(temp_path)
                except Exception as e:
                    logger.error("Error processing image for key '%s': %s", key, str(e))
                    raise HTTPException(status_code=500,
                                        detail=f"Error processing image for {key}: {str(e)}")
    return temporary_images, user_inputs

def clean_up_images(temporary_images):
    """
    Deletes the temporary image files provided in the temporary_images list.
    Args:
        temporary_images (list): List of temporary file paths to be removed.
    """
    if not temporary_images:
        return

    for temp_file_path in temporary_images:
        if os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.info("Removed temporary file: %s", temp_file_path)
            except Exception as e:
                logger.error("Error removing temporary file '%s': %s", temp_file_path, str(e))