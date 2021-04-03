import sys, getopt, os
from MotionDetector import motion_trap
from AIDetector import AI_trap

def main(argv):
    """
    Main method acts as a control function, starting the application and running
    the required methods.

    @param argv: list of command line arguments passed when the program is run.
    """
    video_path, model_path = decode_args(argv)
    check_file_exists(video_path, model_path)
    run_chosen_mode(video_path, model_path)

def decode_args(argv):
    """
    Method parses the command line arguments.

    @param argv: list of command line arguments passed when the program is run.
    @return: If argument not given returns None, else returns the path given in the command line args.
    """
    video_path = None
    model_path = None

    try: 
        opts, args = getopt.getopt(argv, 'hv:m:')
    except getopt.GetoptError:
        print("Usage: {name}.py -v {video path} -m {model path}")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print("Usage: {name}.py -v {video path} -m {model path}")
            sys.exit(2)
        elif opt == '-v':
            video_path = arg
        elif opt == '-m':
            model_path = arg

    return video_path, model_path

def check_file_exists(video_path=None, model_path=None):
    """
    Method to check if command line arguments are calid files.

    @param video_path: The provided path to the video to use.
    @param model_path: The provided path to the model to use.
    @throws: IOError if file not found.
    """
    if video_path is None and model_path is None:
        return
    if video_path is not None and os.path.isfile(video_path):
        return
    if model_path is not None and os.path.isfile(model_path):
        return
    
    raise IOError("File not found")
    


def run_chosen_mode(video_path, model_path):
    """
    Based on what command line arguments were provided, runs the appropriate version of the application.

    @param video_path: The provided path to the video to use.
    @param model_path: The provided path to the model to use.
    """
    if video_path is None and model_path is None:
        motion_trap()
    elif video_path is None and model_path is not None:
        AI_trap(model_path)
    elif video_path is not None and model_path is None:
        motion_trap(video_path)
    else:
        AI_trap(model_path, video_path)

if __name__ == "__main__":
   main(sys.argv[1:])