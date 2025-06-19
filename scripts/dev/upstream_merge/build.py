from shell_commands import *

def build_images(clean_build=False):
    """
    Build the images for the project.
    This function orchestrates the steps required to build the images, including
    setting up the Docker environment, cleaning build feeds and images, and building
    the core feeds and images.
    :param clean_build: A boolean indicating whether to clean the build feeds and images.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    # Step 1: Set up the Docker environment
    docker = start_docker_setup()
    if docker[0] != 0:
        return docker
    print("\nDocker setup completed.")
    
    if clean_build:
        # Step 2: Clean the build feeds and images
        clean = clean_build_feeds_and_images()
        if clean[0] != 0:
            return clean
        print("\nClean build feeds and images completed.")
    else:
        # Step 2: Build the core feeds
        core_feeds = build_core_feeds()
        if core_feeds[0] != 0:
            return core_feeds
        print("\nCore feeds build completed.")   

        # Step 3: Build the core images
        core_images = build_core_images()
        if core_images[0] != 0:
            return core_images
        print("\nCore images build completed.")

    # Return success if all steps are completed
    return (0, None)

def clean_build_feeds_and_images():
    """
    Clean the build feeds and images.
    This step involves running the script to clean the build feeds and images.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    print("\nCleaning build feeds and images...\n")
    return execute_and_stream_cmd_output("bash scripts/pipelines/clean_build.core-feeds_and_core-images.sh --org")

def start_docker_setup():
    """
    Start the Docker setup process.
    This script initializes the Docker environment required for building images.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    print("\nStarting Docker setup...\n")
    return execute_and_stream_cmd_output("bash ./docker/create-build-nilrt.sh")

def build_core_feeds():
    """
    Build the core feeds.
    This step involves running the script to build the core feeds required for the images.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    print("\nBuilding core feeds...\n")
    return execute_and_stream_cmd_output("bash scripts/pipelines/build.core-feeds.sh --org")

def build_core_images():
    """
    Build the core images.
    This step involves running the script to build the core images for the project.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    print("\nBuilding core images...\n")
    return execute_and_stream_cmd_output("bash scripts/pipelines/build.core-images.sh --org")

if __name__ == "__main__":
    status_code, message = build_images()
    
    if status_code == 0:
        print("\nBuild completed successfully.")
    else:
        print(f"\nBuild failed with status code {status_code}. Error: {message}")
