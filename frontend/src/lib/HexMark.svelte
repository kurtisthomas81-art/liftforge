<script>
  export let size = 80;
  export let sceneOpacity = 0.38;
  export let heroMode = false;

  const cx = 50, cy = 50, R = 46;

  function hexPoints(r) {
    return Array.from({length: 6}, (_, i) => {
      const a = Math.PI / 180 * (60 * i - 90);
      return `${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`;
    }).join(' ');
  }

  $: uid = `hm-${size}-${Math.round(sceneOpacity * 100)}`;
  $: hex = hexPoints(R);
  $: hexInner = hexPoints(R * 0.88);

  const sparks = [
    [38,41,2.8],[34,37,1.8],[42,36,1.6],[30,42,1.4],[44,39,1.2],[36,34,1.0]
  ];
</script>

<svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="hg-{uid}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f04070"/>
      <stop offset="100%" stop-color="#b82040"/>
    </linearGradient>
    <clipPath id="hc-{uid}"><polygon points={hex}/></clipPath>
  </defs>

  <!-- Hex body -->
  <polygon points={hex} fill="url(#hg-{uid})"/>
  <polygon points={hexInner} fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>

  <!-- Scene -->
  <g clip-path="url(#hc-{uid})" opacity={sceneOpacity}>
    <!-- Anvil horn -->
    <path d="M30,47 Q20,47 11,51 Q20,55 30,55 Z" fill="black"/>
    <!-- Anvil top face -->
    <rect x="28" y="44" width="52" height="12" rx="2" fill="black"/>
    <!-- Anvil waist -->
    <path d="M36,56 L38,68 L66,68 L68,56 Z" fill="black"/>
    <!-- Anvil base -->
    <rect x="26" y="67" width="52" height="10" rx="2.5" fill="black"/>

    <!-- Dumbbell -->
    <g transform="translate(42,26) rotate(-45)">
      <polygon points="-30,-15 -22,-19 -14,-15 -14,15 -22,19 -30,15" fill="black"/>
      <polygon points="-28,-11 -22,-14 -16,-11 -16,11 -22,14 -28,11" fill="rgba(255,255,255,0.07)"/>
      <circle cx="-22" cy="0" r="4" fill="rgba(255,255,255,0.11)"/>
      <rect x="-14" y="-5.5" width="4" height="11" rx="1" fill="rgba(0,0,0,0.95)"/>
      <rect x="-10" y="-3.5" width="20" height="7" rx="3.5" fill="black"/>
      {#each [-5,0,5] as kx}
        <rect x={kx} y="-3.5" width="1.2" height="7" rx="0.4" fill="rgba(255,255,255,0.07)"/>
      {/each}
      <rect x="10" y="-5.5" width="4" height="11" rx="1" fill="rgba(0,0,0,0.95)"/>
      <polygon points="14,-15 22,-19 30,-15 30,15 22,19 14,15" fill="black"/>
      <polygon points="16,-11 22,-14 28,-11 28,11 22,14 16,11" fill="rgba(255,255,255,0.07)"/>
      <circle cx="22" cy="0" r="4" fill="rgba(255,255,255,0.11)"/>
    </g>

    {#if heroMode}
      {#each sparks as [sx, sy, sr], i}
        <circle cx={sx} cy={sy} r={sr}
          fill={i % 2 === 0 ? "#e8a036" : "#e8d836"}
          opacity={0.75 - i * 0.1}/>
      {/each}
    {/if}
  </g>

  <!-- LF monogram -->
  <rect x="24" y="31" width="8.5" height="32" rx="2" fill="white"/>
  <rect x="24" y="57.5" width="19" height="7" rx="2" fill="white"/>
  <rect x="44.5" y="29" width="2" height="36" rx="1" fill="rgba(255,255,255,0.18)"/>
  <rect x="48.5" y="31" width="8.5" height="32" rx="2" fill="white"/>
  <rect x="48.5" y="31" width="22" height="7" rx="2" fill="white"/>
  <rect x="48.5" y="44" width="16" height="6" rx="2" fill="white"/>
</svg>
