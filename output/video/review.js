'use strict';

(async () => {
  const video = document.querySelector('#full-review');
  const list = document.querySelector('#transcript');
  const status = document.querySelector('#transcript-status');
  try {
    const response = await fetch('LeaseRadar_Full_Browser_Review_20261028.captions.json');
    if (!response.ok) throw new Error('逐段稿加载失败');
    const data = await response.json();
    if (data.schema !== 1 || data.human_listening_review !== false || data.ready_to_submit !== false ||
        !Number.isFinite(data.duration) || !Array.isArray(data.scenes) || data.scenes.length !== 10 ||
        data.scenes.some((scene, index) => !scene || typeof scene.title !== 'string' ||
          typeof scene.text !== 'string' || !Number.isFinite(scene.start) || !Number.isFinite(scene.end) ||
          scene.start < 0 || scene.end <= scene.start || scene.end > data.duration ||
          (index > 0 && scene.start < data.scenes[index - 1].end))) throw new Error('逐段稿无效');
    for (const [index, scene] of data.scenes.entries()) {
      const item = document.createElement('li');
      const button = document.createElement('button');
      const time = `${Math.floor(scene.start / 60)}:${String(Math.floor(scene.start % 60)).padStart(2, '0')}`;
      button.textContent = `${time} · ${scene.title}`;
      button.type = 'button';
      button.addEventListener('click', () => {
        video.currentTime = scene.start;
        status.textContent = `已定位第 ${index + 1} 段：${scene.title}。点击播放器播放。`;
      });
      const text = document.createElement('p');
      text.textContent = scene.text;
      item.append(button, text);
      list.append(item);
    }
    status.textContent = '可点击十段标题定位，核对后记录时间码。字幕句内时码为估算。';
  } catch {
    status.textContent = '逐段稿未加载。请用本地 HTTP 服务打开此页，或下载字幕和逐段稿查看。';
  }
})();
