SELECT ts,dur,name FROM slice WHERE name GLOB '*DrawFrames*' OR name GLOB '*Vulkan finish frame*';
