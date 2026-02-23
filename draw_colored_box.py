import cv2

def get_confidence_color(value):
    """
    Takes a value from 0.0 to 1.0.
    Returns a BGR color tuple ranging from Red (0) to Green (1).
    """
    # Clamp the value to strictly fall between 0.0 and 1.0
    value = max(0.0, min(1.0, value))
    
    # Calculate the BGR colors
    blue = 0
    green = int(255 * value)          # Increases as confidence goes up
    red = int(255 * (1.0 - value))    # Decreases as confidence goes up
    
    return (blue, green, red)

def find_and_draw_box(main_image_path, template_path, output_path="output.jpg"):
    """
    Finds a template image inside a main image and draws a bounding box.
    The color of the box indicates the confidence of the match.
    """
    # 1. Load the images
    main_img = cv2.imread(main_image_path)
    template_img = cv2.imread(template_path)

    if main_img is None or template_img is None:
        print("Error: Could not load one or both images. Check the file paths.")
        return

    # 2. Convert both images to grayscale for matching
    main_gray = cv2.cvtColor(main_img, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)

    # 3. Get the width and height of the template piece
    h, w = template_gray.shape

    # 4. Perform the template matching
    result = cv2.matchTemplate(main_gray, template_gray, cv2.TM_CCOEFF_NORMED)

    # 5. Find the coordinates and confidence score of the best match
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # 6. Calculate box coordinates
    top_left = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)

    # 7. Generate the color based on the match confidence (max_val)
    box_color = get_confidence_color(max_val)
    
    print(f"Match Confidence: {max_val:.2f}")
    print(f"Drawing box with BGR color: {box_color}")

    # 8. Draw the bounding box
    cv2.rectangle(main_img, top_left, bottom_right, box_color, 2)

    # 9. Save and display the result
    cv2.imwrite(output_path, main_img)
    print(f"Success! Result saved to {output_path}")
    
    # Optional: Display the image on screen
    cv2.imshow("Found Match", main_img)
    cv2.waitKey(0) # Press any key to close the window
    cv2.destroyAllWindows()

# --- Example Usage ---
if __name__ == "__main__":
    # Replace these strings with the actual paths to your images
    MAIN_IMAGE = "fruits.png"
    PART_IMAGE = "fruit_crop.png"
    
    find_and_draw_box(MAIN_IMAGE, PART_IMAGE)