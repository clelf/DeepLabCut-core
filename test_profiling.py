# -*- coding: utf-8 -*-

import os

import deeplabcutcore as dlc

from pathlib import Path
import pandas as pd
import numpy as np
import platform


#s Jump to lines 79, 83, 102, 109 for functions that are getting profiled
# Set-up for running functions of interest
task='Testcore' # Enter the name of your experiment Task
scorer='Clem' # Enter the name of the experimenter/labeler

basepath=os.path.dirname(os.path.abspath('test_profiling.py'))
videoname='reachingvideo1'

video = [
    os.path.join(
        basepath, "Reaching-Mackenzie-2018-08-30", "videos", videoname + ".avi"
    )
]

dfolder=None
net_type='resnet_50' #'mobilenet_v2_0.35' #'resnet_50'
augmenter_type='default'
augmenter_type2='imgaug'

if platform.system() == 'Darwin' or platform.system()=='Windows':
    print("On Windows/OSX tensorpack is not tested by default.")
    augmenter_type3='imgaug'
else:
    augmenter_type3='tensorpack' #Does not work on WINDOWS

numiter=5

path_config_file=dlc.create_new_project(task,scorer,video,copy_videos=True)

cfg=dlc.auxiliaryfunctions.read_config(path_config_file)
cfg['numframes2pick']=5
cfg['pcutoff']=0.01
cfg['TrainingFraction']=[.8]
cfg['skeleton']=[['bodypart1','bodypart2'],['bodypart1','bodypart3']]

dlc.auxiliaryfunctions.write_config(path_config_file,cfg)

dlc.extract_frames(path_config_file,mode='automatic',userfeedback=False)

frames=os.listdir(os.path.join(cfg['project_path'],'labeled-data',videoname))
#As this next step is manual, we update the labels by putting them on the diagonal (fixed for all frames)
for index,bodypart in enumerate(cfg['bodyparts']):
        columnindex = pd.MultiIndex.from_product([[scorer], [bodypart], ['x', 'y']],names=['scorer', 'bodyparts', 'coords'])
        frame = pd.DataFrame(100+np.ones((len(frames),2))*50*index, columns = columnindex, index = [os.path.join('labeled-data',videoname,fn) for fn in frames])
        if index==0:
            dataFrame=frame
        else:
            dataFrame = pd.concat([dataFrame, frame],axis=1)

dataFrame.to_csv(os.path.join(cfg['project_path'],'labeled-data',videoname,"CollectedData_" + scorer + ".csv"))
dataFrame.to_hdf(os.path.join(cfg['project_path'],'labeled-data',videoname,"CollectedData_" + scorer + '.h5'),'df_with_missing',format='table', mode='w')


dlc.check_labels(path_config_file)

dlc.create_training_dataset(path_config_file,net_type=net_type,augmenter_type=augmenter_type)

posefile=os.path.join(cfg['project_path'],'dlc-models/iteration-'+str(cfg['iteration'])+'/'+ cfg['Task'] + cfg['date'] + '-trainset' + str(int(cfg['TrainingFraction'][0] * 100)) + 'shuffle' + str(1),'train/pose_cfg.yaml')

DLC_config=dlc.auxiliaryfunctions.read_plainconfig(posefile)
DLC_config['save_iters']=numiter
DLC_config['display_iters']=2
DLC_config['multi_step']=[[0.001,numiter]]

dlc.auxiliaryfunctions.write_plainconfig(posefile,DLC_config)

# profile train_network
dlc.train_network(path_config_file)


# profile evaluate_network
dlc.evaluate_network(path_config_file,plotting=True)

try: #you need ffmpeg command line interface
    #subprocess.call(['ffmpeg','-i',video[0],'-ss','00:00:00','-to','00:00:00.4','-c','copy',newvideo])
    newvideo=dlc.ShortenVideo(video[0],start='00:00:00',stop='00:00:00.4',outsuffix='short',outpath=os.path.join(cfg['project_path'],'videos'))
    vname=Path(newvideo).stem
except: # if ffmpeg is broken
    vname='brief'
    newvideo=os.path.join(cfg['project_path'],'videos',vname+'.mp4')
    from moviepy.editor import VideoFileClip,VideoClip
    clip = VideoFileClip(video[0])
    clip.reader.initialize()
    def make_frame(t):
        return clip.get_frame(1)

    newclip = VideoClip(make_frame, duration=1)
    newclip.write_videofile(newvideo,fps=30)

# profile analyze_videos
dlc.analyze_videos(path_config_file, [newvideo], save_as_csv=True, destfolder=dfolder, dynamic=(True, .1, 5))

dlc.create_labeled_video(path_config_file,[newvideo], destfolder=dfolder,save_frames=True)
dlc.plot_trajectories(path_config_file,[newvideo], destfolder=dfolder)


# profile analyze_time_lapse_frames
dlc.analyze_time_lapse_frames(path_config_file,os.path.join(cfg['project_path'],'labeled-data/reachingvideo1/'))


# profile image detection depending on the number of frames: TO DO

# clean CSV from rows with tensorflow built-in functions ...
#from benchmark.profiling import clean_from_tf_rows                
                   

""
"""
pr = cProfile.Profile()
pr.enable()
dlc.train_network(path_config_file)
pr.disable()
s = io.StringIO()
sortby = SortKey.CUMULATIVE
ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
#pr.dump_stats('pr_train_network.txt')
print(s.getvalue())
"""
"""
with cProfile.Profile() as pr:
    dlc.train_network(path_config_file)

pr.dump_stats('pr_train_network.csv')
"""



