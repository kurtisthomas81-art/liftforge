<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let muscles = [];
  let loading = true;
  let error = null;

  const STATUS_COLOR = {
    green: 'var(--success)',
    amber: 'var(--primary)',
    red:   'var(--danger)',
    gray:  '#333333',
  };

  const STATUS_LABEL = {
    green: 'Recovered',
    amber: 'Recovering',
    red:   'Fatigued',
    gray:  'Not logged',
  };

  const STATUS_ORDER = { red: 0, amber: 1, gray: 2, green: 3 };

  onMount(async () => {
    try {
      const data = await api.recovery.getMap();
      muscles = data.muscles.slice().sort(
        (a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status]
      );
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  function color(muscle) {
    const m = muscles.find(m => m.muscle === muscle);
    return m ? STATUS_COLOR[m.status] : '#333333';
  }

  function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  function fmtDays(d) {
    if (d === null || d === undefined) return '—';
    if (d < 1) return `${Math.round(d * 24)}h ago`;
    return `${d.toFixed(1)}d ago`;
  }
</script>

<div class="page">
  <div class="page-header">
    <h2>Recovery Map</h2>
    <p class="subtitle">Muscle readiness based on training recency and effort (RIR — reps left in tank)</p>
    <div class="legend">
      <span class="dot" style="background:var(--success)"></span> Recovered
      <span class="dot" style="background:var(--primary)"></span> Recovering
      <span class="dot" style="background:var(--danger)"></span> Fatigued
      <span class="dot" style="background:#333333; border:1px solid #555"></span> Not logged
    </div>
  </div>

  {#if loading}
    <div class="spinner-wrap"><div class="spinner"></div></div>
  {:else if error}
    <div class="error-box">{error}</div>
  {:else}
    <div class="content">
      <!-- SVG Body Diagrams -->
      <div class="diagrams">
        <!-- Front view -->
        <div class="diagram-wrap">
          <div class="diagram-label">Front</div>
          <svg viewBox="0 0 400 1000" xmlns="http://www.w3.org/2000/svg">

            <!-- === BODY SILHOUETTE — FRONT === -->

            <!-- Head -->
            <ellipse cx="200" cy="58" rx="48" ry="52" fill="#1e2020"/>

            <!-- Neck -->
            <path d="M176,104 C178,118 178,126 176,134 L224,134 C222,126 222,118 224,104 Z" fill="#1e2020"/>

            <!-- Torso: wide shoulders, waist taper, hip flare -->
            <path d="
              M62,136
              C52,138 38,146 32,158
              C26,170 28,190 30,220
              C32,250 34,280 34,310
              C30,330 26,352 126,368
              C134,370 166,372 200,372
              C234,372 266,370 274,368
              C374,352 370,330 366,310
              C366,280 368,250 370,220
              C372,190 374,170 368,158
              C362,146 348,138 338,136
              C310,130 270,126 200,126
              C130,126 90,130 62,136
              Z" fill="#1e2020"/>

            <!-- Hips bridge between torso and thighs -->
            <path d="
              M126,368 C110,370 96,372 94,380 L94,448 L188,448 L188,380 C186,372 152,368 126,368 Z
            " fill="#1e2020"/>
            <path d="
              M274,368 C290,370 304,372 306,380 L306,448 L212,448 L212,380 C214,372 248,368 274,368 Z
            " fill="#1e2020"/>

            <!-- Left upper arm — angled outward, tapered tube -->
            <path d="
              M62,136
              C48,140 34,152 32,170
              C30,200 32,260 34,320
              C35,340 38,358 44,368
              C50,376 58,378 66,374
              C74,370 78,360 78,340
              C80,300 80,240 78,190
              C76,160 72,140 62,136
              Z" fill="#1e2020"/>

            <!-- Right upper arm -->
            <path d="
              M338,136
              C352,140 366,152 368,170
              C370,200 368,260 366,320
              C365,340 362,358 356,368
              C350,376 342,378 334,374
              C326,370 322,360 322,340
              C320,300 320,240 322,190
              C324,160 328,140 338,136
              Z" fill="#1e2020"/>

            <!-- Left forearm — narrower, tapers toward wrist -->
            <path d="
              M44,368
              C38,374 30,384 28,402
              C26,424 28,464 30,496
              C31,512 34,524 40,530
              C46,536 54,534 60,528
              C66,522 68,508 68,492
              C68,466 66,426 64,404
              C62,386 56,374 44,368
              Z" fill="#1e2020"/>

            <!-- Right forearm -->
            <path d="
              M356,368
              C362,374 370,384 372,402
              C374,424 372,464 370,496
              C369,512 366,524 360,530
              C354,536 346,534 340,528
              C334,522 332,508 332,492
              C332,466 334,426 336,404
              C338,386 344,374 356,368
              Z" fill="#1e2020"/>

            <!-- Left thigh — wider at hip, slight outward bow -->
            <path d="
              M94,448
              C82,452 78,464 78,484
              C76,520 76,580 80,636
              C82,664 86,700 96,726
              C104,744 118,752 140,752
              C162,752 176,744 184,726
              C192,706 194,672 194,640
              C196,584 194,522 190,486
              C188,466 184,452 174,448
              Z" fill="#1e2020"/>

            <!-- Right thigh -->
            <path d="
              M306,448
              C318,452 322,464 322,484
              C324,520 324,580 320,636
              C318,664 314,700 304,726
              C296,744 282,752 260,752
              C238,752 224,744 216,726
              C208,706 206,672 206,640
              C204,584 206,522 210,486
              C212,466 216,452 226,448
              Z" fill="#1e2020"/>

            <!-- Left knee cap -->
            <ellipse cx="144" cy="740" rx="44" ry="22" fill="#1e2020"/>

            <!-- Right knee cap -->
            <ellipse cx="256" cy="740" rx="44" ry="22" fill="#1e2020"/>

            <!-- Left lower leg — wide at knee, tapers to ankle -->
            <path d="
              M100,752
              C92,764 88,784 88,810
              C88,850 92,890 98,920
              C102,938 110,950 126,954
              C140,958 156,954 164,942
              C172,930 176,910 176,882
              C178,848 176,804 172,768
              C168,754 160,746 148,744
              Z" fill="#1e2020"/>

            <!-- Right lower leg -->
            <path d="
              M300,752
              C308,764 312,784 312,810
              C312,850 308,890 302,920
              C298,938 290,950 274,954
              C260,958 244,954 236,942
              C228,930 224,910 224,882
              C222,848 224,804 228,768
              C232,754 240,746 252,744
              Z" fill="#1e2020"/>

            <!-- Left foot -->
            <ellipse cx="144" cy="966" rx="52" ry="26" fill="#1e2020"/>

            <!-- Right foot -->
            <ellipse cx="256" cy="966" rx="52" ry="26" fill="#1e2020"/>


            <!-- === FRONT MUSCLE OVERLAYS === -->

            <!-- Chest / Left pec — fan from sternum outward -->
            <path d="
              M195,152
              C178,152 148,158 122,172
              C100,184 88,200 90,228
              C92,250 104,272 128,284
              C152,296 178,294 195,280
              C198,272 200,260 200,240
              C200,210 198,180 195,152
              Z"
              fill={color('chest')} opacity="0.85"/>

            <!-- Chest / Right pec -->
            <path d="
              M205,152
              C222,152 252,158 278,172
              C300,184 312,200 310,228
              C308,250 296,272 272,284
              C248,296 222,294 205,280
              C202,272 200,260 200,240
              C200,210 202,180 205,152
              Z"
              fill={color('chest')} opacity="0.85"/>

            <!-- Shoulders / Left anterior deltoid cap -->
            <path d="
              M62,136
              C44,136 32,148 30,164
              C28,180 36,200 52,214
              C64,224 80,228 96,220
              C108,214 114,200 112,182
              C110,162 96,144 80,138
              C74,136 68,135 62,136
              Z"
              fill={color('shoulders')} opacity="0.85"/>

            <!-- Shoulders / Right anterior deltoid cap -->
            <path d="
              M338,136
              C356,136 368,148 370,164
              C372,180 364,200 348,214
              C336,224 320,228 304,220
              C292,214 286,200 288,182
              C290,162 304,144 320,138
              C326,136 332,135 338,136
              Z"
              fill={color('shoulders')} opacity="0.85"/>

            <!-- Biceps / Left teardrop on anterior upper arm -->
            <path d="
              M36,244
              C30,256 28,280 30,310
              C32,332 38,354 50,366
              C56,372 64,372 70,366
              C76,358 78,340 76,316
              C74,286 68,260 58,246
              C52,238 42,238 36,244
              Z"
              fill={color('biceps')} opacity="0.85"/>

            <!-- Biceps / Right teardrop -->
            <path d="
              M364,244
              C370,256 372,280 370,310
              C368,332 362,354 350,366
              C344,372 336,372 330,366
              C324,358 322,340 324,316
              C326,286 332,260 342,246
              C348,238 358,238 364,244
              Z"
              fill={color('biceps')} opacity="0.85"/>

            <!-- Abs — 3 paired sections, 6 total with Q beziers -->
            <!-- Top-left -->
            <path d="M138,308 Q140,304 158,304 Q176,304 178,308 L178,352 Q176,356 158,356 Q140,356 138,352 Z"
                  fill={color('abs')} opacity="0.85"/>
            <!-- Top-right -->
            <path d="M222,308 Q224,304 242,304 Q260,304 262,308 L262,352 Q260,356 242,356 Q224,356 222,352 Z"
                  fill={color('abs')} opacity="0.85"/>
            <!-- Mid-left -->
            <path d="M138,360 Q140,356 158,356 Q176,356 178,360 L178,400 Q176,404 158,404 Q140,404 138,400 Z"
                  fill={color('abs')} opacity="0.85"/>
            <!-- Mid-right -->
            <path d="M222,360 Q224,356 242,356 Q260,356 262,360 L262,400 Q260,404 242,404 Q224,404 222,400 Z"
                  fill={color('abs')} opacity="0.85"/>
            <!-- Bottom-left — shorter, slight taper -->
            <path d="M140,408 Q142,404 158,404 Q174,404 176,408 L174,428 Q172,432 158,432 Q144,432 142,428 Z"
                  fill={color('abs')} opacity="0.85"/>
            <!-- Bottom-right -->
            <path d="M224,408 Q226,404 242,404 Q258,404 260,408 L258,428 Q256,432 242,432 Q228,432 226,428 Z"
                  fill={color('abs')} opacity="0.85"/>

            <!-- Quads / Left anterior thigh sweep -->
            <path d="
              M94,460
              C82,464 78,478 78,500
              C76,536 78,596 84,646
              C88,674 96,706 110,728
              C120,744 134,750 148,748
              C162,746 174,738 182,722
              C190,704 192,670 192,638
              C194,590 192,532 188,494
              C184,468 176,454 162,450
              C144,446 110,454 94,460
              Z"
              fill={color('quads')} opacity="0.85"/>
            <!-- VMO teardrop / left -->
            <ellipse cx="120" cy="726" rx="22" ry="28" transform="rotate(-18,120,726)"
                     fill={color('quads')} opacity="0.85"/>

            <!-- Quads / Right -->
            <path d="
              M306,460
              C318,464 322,478 322,500
              C324,536 322,596 316,646
              C312,674 304,706 290,728
              C280,744 266,750 252,748
              C238,746 226,738 218,722
              C210,704 208,670 208,638
              C206,590 208,532 212,494
              C216,468 224,454 238,450
              C256,446 290,454 306,460
              Z"
              fill={color('quads')} opacity="0.85"/>
            <!-- VMO teardrop / right -->
            <ellipse cx="280" cy="726" rx="22" ry="28" transform="rotate(18,280,726)"
                     fill={color('quads')} opacity="0.85"/>

            <!-- Calves / Left gastrocnemius belly, front-visible portion -->
            <path d="
              M100,754
              C90,766 86,790 86,822
              C86,858 92,896 102,924
              C108,940 118,950 132,950
              C148,950 160,940 166,922
              C174,898 174,860 170,824
              C166,790 158,766 146,754
              C138,748 126,748 118,752
              C110,756 104,754 100,754
              Z"
              fill={color('calves')} opacity="0.85"/>

            <!-- Calves / Right -->
            <path d="
              M300,754
              C310,766 314,790 314,822
              C314,858 308,896 298,924
              C292,940 282,950 268,950
              C252,950 240,940 234,922
              C226,898 226,860 230,824
              C234,790 242,766 254,754
              C262,748 274,748 282,752
              C290,756 296,754 300,754
              Z"
              fill={color('calves')} opacity="0.85"/>

          </svg>
        </div>

        <!-- Back view -->
        <div class="diagram-wrap">
          <div class="diagram-label">Back</div>
          <svg viewBox="0 0 400 1000" xmlns="http://www.w3.org/2000/svg">

            <!-- === BODY SILHOUETTE — BACK (identical shape) === -->

            <!-- Head -->
            <ellipse cx="200" cy="58" rx="48" ry="52" fill="#1e2020"/>

            <!-- Neck -->
            <path d="M176,104 C178,118 178,126 176,134 L224,134 C222,126 222,118 224,104 Z" fill="#1e2020"/>

            <!-- Torso -->
            <path d="
              M62,136
              C52,138 38,146 32,158
              C26,170 28,190 30,220
              C32,250 34,280 34,310
              C30,330 26,352 126,368
              C134,370 166,372 200,372
              C234,372 266,370 274,368
              C374,352 370,330 366,310
              C366,280 368,250 370,220
              C372,190 374,170 368,158
              C362,146 348,138 338,136
              C310,130 270,126 200,126
              C130,126 90,130 62,136
              Z" fill="#1e2020"/>

            <!-- Hips -->
            <path d="M126,368 C110,370 96,372 94,380 L94,448 L188,448 L188,380 C186,372 152,368 126,368 Z" fill="#1e2020"/>
            <path d="M274,368 C290,370 304,372 306,380 L306,448 L212,448 L212,380 C214,372 248,368 274,368 Z" fill="#1e2020"/>

            <!-- Left upper arm -->
            <path d="
              M62,136 C48,140 34,152 32,170 C30,200 32,260 34,320
              C35,340 38,358 44,368 C50,376 58,378 66,374
              C74,370 78,360 78,340 C80,300 80,240 78,190
              C76,160 72,140 62,136 Z" fill="#1e2020"/>

            <!-- Right upper arm -->
            <path d="
              M338,136 C352,140 366,152 368,170 C370,200 368,260 366,320
              C365,340 362,358 356,368 C350,376 342,378 334,374
              C326,370 322,360 322,340 C320,300 320,240 322,190
              C324,160 328,140 338,136 Z" fill="#1e2020"/>

            <!-- Left forearm -->
            <path d="
              M44,368 C38,374 30,384 28,402 C26,424 28,464 30,496
              C31,512 34,524 40,530 C46,536 54,534 60,528
              C66,522 68,508 68,492 C68,466 66,426 64,404
              C62,386 56,374 44,368 Z" fill="#1e2020"/>

            <!-- Right forearm -->
            <path d="
              M356,368 C362,374 370,384 372,402 C374,424 372,464 370,496
              C369,512 366,524 360,530 C354,536 346,534 340,528
              C334,522 332,508 332,492 C332,466 334,426 336,404
              C338,386 344,374 356,368 Z" fill="#1e2020"/>

            <!-- Left thigh -->
            <path d="
              M94,448 C82,452 78,464 78,484 C76,520 76,580 80,636
              C82,664 86,700 96,726 C104,744 118,752 140,752
              C162,752 176,744 184,726 C192,706 194,672 194,640
              C196,584 194,522 190,486 C188,466 184,452 174,448 Z" fill="#1e2020"/>

            <!-- Right thigh -->
            <path d="
              M306,448 C318,452 322,464 322,484 C324,520 324,580 320,636
              C318,664 314,700 304,726 C296,744 282,752 260,752
              C238,752 224,744 216,726 C208,706 206,672 206,640
              C204,584 206,522 210,486 C212,466 216,452 226,448 Z" fill="#1e2020"/>

            <!-- Knee caps -->
            <ellipse cx="144" cy="740" rx="44" ry="22" fill="#1e2020"/>
            <ellipse cx="256" cy="740" rx="44" ry="22" fill="#1e2020"/>

            <!-- Left lower leg -->
            <path d="
              M100,752 C92,764 88,784 88,810 C88,850 92,890 98,920
              C102,938 110,950 126,954 C140,958 156,954 164,942
              C172,930 176,910 176,882 C178,848 176,804 172,768
              C168,754 160,746 148,744 Z" fill="#1e2020"/>

            <!-- Right lower leg -->
            <path d="
              M300,752 C308,764 312,784 312,810 C312,850 308,890 302,920
              C298,938 290,950 274,954 C260,958 244,954 236,942
              C228,930 224,910 224,882 C222,848 224,804 228,768
              C232,754 240,746 252,744 Z" fill="#1e2020"/>

            <!-- Left foot -->
            <ellipse cx="144" cy="966" rx="52" ry="26" fill="#1e2020"/>

            <!-- Right foot -->
            <ellipse cx="256" cy="966" rx="52" ry="26" fill="#1e2020"/>


            <!-- === BACK MUSCLE OVERLAYS (z-order: lats, back, traps, triceps, glutes, hamstrings, calves) === -->

            <!-- Lats / Left wing — armpit sweeping down to lower back -->
            <path d="
              M68,168
              C56,172 46,188 42,210
              C36,240 36,280 40,318
              C42,342 48,366 62,380
              C74,392 90,396 108,388
              C126,380 138,362 144,338
              C150,314 150,282 144,254
              C138,224 126,196 108,178
              C96,166 80,164 68,168
              Z"
              fill={color('lats')} opacity="0.85"/>

            <!-- Lats / Right wing -->
            <path d="
              M332,168
              C344,172 354,188 358,210
              C364,240 364,280 360,318
              C358,342 352,366 338,380
              C326,392 310,396 292,388
              C274,380 262,362 256,338
              C250,314 250,282 256,254
              C262,224 274,196 292,178
              C304,166 320,164 332,168
              Z"
              fill={color('lats')} opacity="0.85"/>

            <!-- Mid back / rhomboids — diamond between lats -->
            <path d="
              M200,162
              C220,162 242,168 256,182
              C264,192 264,212 254,226
              C244,238 224,246 200,248
              C176,246 156,238 146,226
              C136,212 136,192 144,182
              C158,168 180,162 200,162
              Z"
              fill={color('back')} opacity="0.85"/>

            <!-- Trapezius — kite/diamond from neck across upper shoulders -->
            <path d="
              M200,140
              C222,142 256,152 290,168
              C310,178 322,192 314,210
              C306,226 282,236 252,240
              C232,244 216,244 200,244
              C184,244 168,244 148,240
              C118,236 94,226 86,210
              C78,192 90,178 110,168
              C144,152 178,142 200,140
              Z"
              fill={color('traps')} opacity="0.85"/>

            <!-- Triceps / Left posterior upper arm — horseshoe shape -->
            <path d="
              M36,168
              C28,180 26,202 26,232
              C26,268 30,308 38,342
              C42,362 50,378 62,382
              C70,386 78,382 82,372
              C88,358 88,332 84,300
              C80,264 72,228 60,196
              C52,174 44,164 36,168
              Z"
              fill={color('triceps')} opacity="0.85"/>

            <!-- Triceps / Right -->
            <path d="
              M364,168
              C372,180 374,202 374,232
              C374,268 370,308 362,342
              C358,362 350,378 338,382
              C330,386 322,382 318,372
              C312,358 312,332 316,300
              C320,264 328,228 340,196
              C348,174 356,164 364,168
              Z"
              fill={color('triceps')} opacity="0.85"/>

            <!-- Glutes / Left rounded posterior hip -->
            <path d="
              M96,444
              C80,448 68,462 64,484
              C60,508 64,538 80,558
              C94,576 116,584 142,578
              C166,572 184,554 188,530
              C192,506 186,478 172,460
              C158,444 130,438 110,440
              C104,440 100,442 96,444
              Z"
              fill={color('glutes')} opacity="0.85"/>

            <!-- Glutes / Right -->
            <path d="
              M304,444
              C320,448 332,462 336,484
              C340,508 336,538 320,558
              C306,576 284,584 258,578
              C234,572 216,554 212,530
              C208,506 214,478 228,460
              C242,444 270,438 290,440
              C296,440 300,442 304,444
              Z"
              fill={color('glutes')} opacity="0.85"/>

            <!-- Hamstrings / Left two-lobe posterior thigh -->
            <path d="
              M82,562
              C72,578 70,606 72,638
              C74,668 82,700 96,724
              C106,742 120,752 138,750
              C158,748 172,736 180,714
              C188,692 188,658 184,626
              C180,594 170,566 154,550
              C142,538 128,538 116,546
              C104,554 90,558 82,562
              Z"
              fill={color('hamstrings')} opacity="0.85"/>

            <!-- Hamstrings / Right -->
            <path d="
              M318,562
              C328,578 330,606 328,638
              C326,668 318,700 304,724
              C294,742 280,752 262,750
              C242,748 228,736 220,714
              C212,692 212,658 216,626
              C220,594 230,566 246,550
              C258,538 272,538 284,546
              C296,554 310,558 318,562
              Z"
              fill={color('hamstrings')} opacity="0.85"/>

            <!-- Calves / Left posterior gastrocnemius — two-head prominence -->
            <path d="
              M90,756
              C80,770 74,796 72,828
              C70,862 76,900 88,930
              C96,950 108,962 126,962
              C146,962 160,950 168,930
              C178,906 178,864 172,828
              C166,792 154,764 138,752
              C128,746 116,748 108,754
              C100,760 94,756 90,756
              Z"
              fill={color('calves')} opacity="0.85"/>
            <!-- Left inner head -->
            <path d="
              M108,754 C116,750 128,750 138,756
              C148,762 154,780 150,804
              C146,826 134,840 120,840
              C106,840 96,828 94,808
              C92,786 98,764 108,754 Z"
              fill={color('calves')} opacity="0.75"/>

            <!-- Calves / Right posterior gastrocnemius -->
            <path d="
              M310,756
              C320,770 326,796 328,828
              C330,862 324,900 312,930
              C304,950 292,962 274,962
              C254,962 240,950 232,930
              C222,906 222,864 228,828
              C234,792 246,764 262,752
              C272,746 284,748 292,754
              C300,760 306,756 310,756
              Z"
              fill={color('calves')} opacity="0.85"/>
            <!-- Right inner head -->
            <path d="
              M292,754 C284,750 272,750 262,756
              C252,762 246,780 250,804
              C254,826 266,840 280,840
              C294,840 304,828 306,808
              C308,786 302,764 292,754 Z"
              fill={color('calves')} opacity="0.75"/>

          </svg>
        </div>
      </div>

      <!-- Muscle status table -->
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Muscle</th>
              <th>Status</th>
              <th>Last Trained</th>
              <th title="Average Reps In Reserve — higher means more recovery capacity">Avg RIR</th>
            </tr>
          </thead>
          <tbody>
            {#each muscles as m}
              <tr>
                <td class="muscle-name">{capitalize(m.muscle)}</td>
                <td>
                  <span class="badge" style="background:{STATUS_COLOR[m.status]}22; color:{STATUS_COLOR[m.status]}; border-color:{STATUS_COLOR[m.status]}44">
                    {STATUS_LABEL[m.status]}
                  </span>
                </td>
                <td class="muted">{fmtDays(m.days_since_trained)}</td>
                <td class="muted">{m.avg_rir !== null ? m.avg_rir : '—'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>

<style>
  .page {
    padding: 2rem;
    max-width: 900px;
    margin: 0 auto;
  }

  .page-header {
    margin-bottom: 2rem;
  }

  h2 {
    font-size: 1.4rem;
    font-weight: 600;
    color: var(--text);
    margin: 0 0 0.25rem;
  }

  .subtitle {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin: 0 0 1rem;
  }

  .legend {
    display: flex;
    align-items: center;
    gap: 1.2rem;
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  .dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 4px;
    vertical-align: middle;
  }

  .content {
    display: flex;
    gap: 2.5rem;
    align-items: flex-start;
  }

  .diagrams {
    display: flex;
    gap: 1.5rem;
    flex-shrink: 0;
  }

  .diagram-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }

  .diagram-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  svg {
    width: 150px;
    height: auto;
    display: block;
  }

  .table-wrap {
    flex: 1;
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  th {
    text-align: left;
    color: var(--text-muted);
    font-weight: 500;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0 0.75rem 0.6rem;
    border-bottom: 1px solid var(--border);
  }

  td {
    padding: 0.6rem 0.75rem;
    border-bottom: 1px solid var(--border);
    color: var(--text);
  }

  .muscle-name {
    font-weight: 500;
  }

  .muted {
    color: var(--text-muted);
  }

  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.78rem;
    font-weight: 500;
    border: 1px solid transparent;
  }

  .spinner-wrap {
    display: flex;
    justify-content: center;
    padding: 4rem 0;
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--border);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .error-box {
    background: var(--surface);
    border: 1px solid var(--danger);
    color: var(--danger);
    padding: 1rem;
    border-radius: var(--radius);
    font-size: 0.875rem;
  }

  @media (max-width: 640px) {
    .page { padding: 1rem; }
    .content { flex-direction: column; align-items: center; }
    .table-wrap { width: 100%; }
  }
</style>
