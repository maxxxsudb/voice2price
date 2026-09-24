import json,sys
from pathlib import Path
from uuid import uuid4
from pydub import AudioSegment
from audio_preparation import first_channel_pcm
from server import upload_to_object_storage,recognize_via_storage_uri,_get_yc_settings_or_none
root=Path('/tmp/voice-benchmark'); name=sys.argv[1];s=_get_yc_settings_or_none()
audio=AudioSegment.from_file(root/f'{name}.mp3'); channels=audio.split_to_mono()
metadata={'duration':len(audio)/1000,'channels':len(channels),'channel_rms':[x.rms for x in channels],'pcm_channels_identical':len(channels)==2 and channels[0].raw_data==channels[1].raw_data}
with first_channel_pcm(root/f'{name}.mp3') as (path,info):
 uri=upload_to_object_storage(path,f'audio-uploads/benchmark-{uuid4().hex}.pcm',s)
 text,segments=recognize_via_storage_uri(uri,s.api_key,s.folder_id,encoding='LINEAR16_PCM',sample_rate=16000,channels=1,return_segments=True)
result={'name':name,'metadata':metadata,'text':text,'segments':segments}
(root/f'{name}-transcript.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))
