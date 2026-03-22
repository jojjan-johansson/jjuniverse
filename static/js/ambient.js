/* ── JJ Universe — Ambient ljud via YouTube ───────────────────────────────── */

(function () {
  const VIDEO_ID = '10YvqAmK_qs';
  let player   = null;
  let ready    = false;
  let playing  = false;
  let pendingPlay = false;

  /* Gömd YouTube-spelarbehållare */
  const container = document.createElement('div');
  container.id = 'yt-ambient-container';
  container.style.cssText = 'position:fixed;width:1px;height:1px;left:-9999px;top:-9999px;overflow:hidden;';
  const playerEl = document.createElement('div');
  playerEl.id = 'yt-ambient-player';
  container.appendChild(playerEl);
  document.body.appendChild(container);

  /* Ladda YouTube IFrame API */
  const script = document.createElement('script');
  script.src   = 'https://www.youtube.com/iframe_api';
  document.head.appendChild(script);

  window.onYouTubeIframeAPIReady = function () {
    player = new YT.Player('yt-ambient-player', {
      videoId: VIDEO_ID,
      playerVars: {
        autoplay:   0,
        controls:   0,
        loop:       1,
        playlist:   VIDEO_ID,
        rel:        0,
        modestbranding: 1,
      },
      events: {
        onReady: function () {
          ready = true;
          player.setVolume(55);
          if (pendingPlay) doPlay();
        },
      },
    });
  };

  function doPlay() {
    player.playVideo();
    playing     = true;
    pendingPlay = false;
    btn.classList.add('ambient-on');
    btn.setAttribute('aria-label', 'Bakgrundsljud på');
  }

  function doStop() {
    player.pauseVideo();
    playing = false;
    btn.classList.remove('ambient-on');
    btn.setAttribute('aria-label', 'Bakgrundsljud av');
  }

  /* Knapp */
  const btn = document.createElement('button');
  btn.id        = 'ambient-btn';
  btn.title     = 'Sätt på/stäng av bakgrundsljud';
  btn.innerHTML = '♪';
  btn.setAttribute('aria-label', 'Bakgrundsljud av');
  document.body.appendChild(btn);

  btn.addEventListener('click', function () {
    if (playing) {
      doStop();
    } else if (ready) {
      doPlay();
    } else {
      pendingPlay = true; /* spelar så fort API:t är klart */
      btn.classList.add('ambient-on');
    }
  });
})();
