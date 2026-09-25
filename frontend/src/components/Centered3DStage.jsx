import React, { useEffect, useRef, useState, useCallback } from 'react';
import heroEmblemBase from '../assets/sections/hero_emblem_base.png';

// Dynamically import all 240 frames from MODELFORGE_FRAMES
const frameModules = import.meta.glob('../assets/MODELFORGE_FRAMES/*.jpg', {
  eager: true,
  import: 'default',
});

// Sort frames numerically 001 -> 240
const FRAME_URLS = Object.entries(frameModules)
  .sort(([pathA], [pathB]) => {
    const numA = parseInt(pathA.match(/(\d+)\.jpg/)?.[1] || '0', 10);
    const numB = parseInt(pathB.match(/(\d+)\.jpg/)?.[1] || '0', 10);
    return numA - numB;
  })
  .map(([, url]) => url);

// Dynamically import all 204 frames from MODELFORGE_FRAMES1 for the final continuous loop
const frame1Modules = import.meta.glob('../assets/MODELFORGE_FRAMES1/*.jpg', {
  eager: true,
  import: 'default',
});

const FRAME1_URLS = Object.entries(frame1Modules)
  .sort(([pathA], [pathB]) => {
    const numA = parseInt(pathA.match(/(\d+)\.jpg/)?.[1] || '0', 10);
    const numB = parseInt(pathB.match(/(\d+)\.jpg/)?.[1] || '0', 10);
    return numA - numB;
  })
  .map(([, url]) => url);

// Dynamically import all 300 frames from MODELFORGE_FRAMES2 for the Hero idle rotating container
const frame2Modules = import.meta.glob('../assets/MODELFORGE_FRAMES2/*.jpg', {
  eager: true,
  import: 'default',
});

const FRAME2_URLS = Object.entries(frame2Modules)
  .sort(([pathA], [pathB]) => {
    const numA = parseInt(pathA.match(/(\d+)\.jpg/)?.[1] || '0', 10);
    const numB = parseInt(pathB.match(/(\d+)\.jpg/)?.[1] || '0', 10);
    return numA - numB;
  })
  .map(([, url]) => url);

export default function Centered3DStage({
  scrollProgress = 0,
  activeChapter = 0,
  onHeroIntroComplete = null,
}) {
  const canvasRef = useRef(null);
  const imagesRef = useRef([]);
  const imagesRef1 = useRef([]);
  const imagesRef2 = useRef([]);
  const heroBaseImgRef = useRef(null);
  const [loadedCount, setLoadedCount] = useState(0);
  const [introComplete, setIntroComplete] = useState(false);

  // Animation state references
  const currentFrameRef = useRef(0);
  const targetFrameRef = useRef(0);
  const heroIntroPlayingRef = useRef(true);
  const heroIntroCompleteRef = useRef(false);
  const heroIdleLoopTimeRef = useRef(0);
  const finalLoopTimeRef = useRef(0);
  const animationFrameIdRef = useRef(null);

  // Preload main frames progressively
  useEffect(() => {
    const total = FRAME_URLS.length;
    if (total === 0) return;

    imagesRef.current = new Array(total);
    let loaded = 0;

    // Phase A: Preload Hero frames 001-048 immediately (Hero Intro sequence)
    const heroFrameCount = Math.min(48, total);
    for (let i = 0; i < heroFrameCount; i++) {
      const img = new Image();
      img.src = FRAME_URLS[i];
      img.onload = () => {
        loaded++;
        setLoadedCount(loaded);
      };
      imagesRef.current[i] = img;
    }

    // Phase B: Preload remaining frames 049-240 in background
    const timer = setTimeout(() => {
      for (let i = heroFrameCount; i < total; i++) {
        const img = new Image();
        img.src = FRAME_URLS[i];
        img.onload = () => {
          loaded++;
          setLoadedCount(loaded);
        };
        imagesRef.current[i] = img;
      }
    }, 50);

    return () => clearTimeout(timer);
  }, []);

  // Preload base hero emblem
  useEffect(() => {
    const img = new Image();
    img.src = heroEmblemBase;
    heroBaseImgRef.current = img;
  }, []);

  // Preload MODELFORGE_FRAMES1 for the final continuous loop
  useEffect(() => {
    const total = FRAME1_URLS.length;
    if (total === 0) return;

    imagesRef1.current = new Array(total);
    const timer = setTimeout(() => {
      for (let i = 0; i < total; i++) {
        const img = new Image();
        img.src = FRAME1_URLS[i];
        imagesRef1.current[i] = img;
      }
    }, 150);

    return () => clearTimeout(timer);
  }, []);

  // Preload MODELFORGE_FRAMES2 for Hero idle rotating container
  useEffect(() => {
    const total = FRAME2_URLS.length;
    if (total === 0) return;

    imagesRef2.current = new Array(total);
    // Preload first 60 frames immediately for quick start
    const priorityCount = Math.min(60, total);
    for (let i = 0; i < priorityCount; i++) {
      const img = new Image();
      img.src = FRAME2_URLS[i];
      imagesRef2.current[i] = img;
    }

    // Preload remaining frames
    const timer = setTimeout(() => {
      for (let i = priorityCount; i < total; i++) {
        const img = new Image();
        img.src = FRAME2_URLS[i];
        imagesRef2.current[i] = img;
      }
    }, 80);

    return () => clearTimeout(timer);
  }, []);

  // Draw frame to canvas with pure black background integration
  const drawFrame = useCallback((frameIndex) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const clampedIndex = Math.max(0, Math.min(FRAME_URLS.length - 1, Math.round(frameIndex)));
    const img = imagesRef.current[clampedIndex];

    // Clear to pure black to match frame borders and dark theme
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (img && img.complete && img.naturalWidth > 0) {
      const hRatio = canvas.width / img.naturalWidth;
      const vRatio = canvas.height / img.naturalHeight;
      const ratio = Math.min(hRatio, vRatio);

      const centerShiftX = (canvas.width - img.naturalWidth * ratio) / 2;
      const centerShiftY = (canvas.height - img.naturalHeight * ratio) / 2;

      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';

      ctx.drawImage(
        img,
        0,
        0,
        img.naturalWidth,
        img.naturalHeight,
        centerShiftX,
        centerShiftY,
        img.naturalWidth * ratio,
        img.naturalHeight * ratio
      );
    }
  }, []);

  // Draw frame from MODELFORGE_FRAMES1 with pure black integration
  const drawFrame1 = useCallback((frameIndex) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const clampedIndex = Math.max(0, Math.min(FRAME1_URLS.length - 1, Math.floor(frameIndex)));
    const img = imagesRef1.current[clampedIndex];

    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (img && img.complete && img.naturalWidth > 0) {
      const hRatio = canvas.width / img.naturalWidth;
      const vRatio = canvas.height / img.naturalHeight;
      const ratio = Math.min(hRatio, vRatio);

      const centerShiftX = (canvas.width - img.naturalWidth * ratio) / 2;
      const centerShiftY = (canvas.height - img.naturalHeight * ratio) / 2;

      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';

      ctx.drawImage(
        img,
        0,
        0,
        img.naturalWidth,
        img.naturalHeight,
        centerShiftX,
        centerShiftY,
        img.naturalWidth * ratio,
        img.naturalHeight * ratio
      );
    }
  }, []);

  // Draw Hero Idle State: Rotating container (MODELFORGE_FRAMES2) inside the logo emblem
  const drawHeroIdleComposite = useCallback((frame2Index) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear to pure black
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const baseImg = heroBaseImgRef.current || imagesRef.current[47];
    if (!baseImg || !baseImg.complete || baseImg.naturalWidth === 0) {
      drawFrame(47);
      return;
    }

    const hRatio = canvas.width / baseImg.naturalWidth;
    const vRatio = canvas.height / baseImg.naturalHeight;
    const ratio = Math.min(hRatio, vRatio);

    const baseW = baseImg.naturalWidth * ratio;
    const baseH = baseImg.naturalHeight * ratio;
    const baseX = (canvas.width - baseW) / 2;
    const baseY = (canvas.height - baseH) / 2;

    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';

    // 1. Draw base logo emblem (Frame 048 with container cavity)
    ctx.globalCompositeOperation = 'source-over';
    ctx.drawImage(
      baseImg,
      0,
      0,
      baseImg.naturalWidth,
      baseImg.naturalHeight,
      baseX,
      baseY,
      baseW,
      baseH
    );

    // 2. Draw rotating container (MODELFORGE_FRAMES2) seamlessly inside the logo cavity
    if (FRAME2_URLS.length > 0 && imagesRef2.current.length > 0) {
      const clampedIndex = Math.max(0, Math.min(FRAME2_URLS.length - 1, Math.floor(frame2Index)));
      const rotImg = imagesRef2.current[clampedIndex];

      if (rotImg && rotImg.complete && rotImg.naturalWidth > 0) {
        // Container scale relative to base: 0.355
        const cW = baseW * 0.355;
        const cH = baseH * 0.355;

        // Clip source to omit floor reflection (keep container y: 0 to 635 out of 720)
        const sourceH = Math.min(rotImg.naturalHeight, (rotImg.naturalHeight * 635) / 720);
        const cropH = cH * (635 / 720);

        // Center inside the logo cavity: cx = 0.50 * baseW, cy = 0.475 * baseH
        const dx = baseX + baseW * 0.50 - cW * 0.50;
        const dy = baseY + baseH * 0.475 - cH * 0.52;

        ctx.globalCompositeOperation = 'screen';
        ctx.drawImage(
          rotImg,
          0,
          0,
          rotImg.naturalWidth,
          sourceH,
          dx,
          dy,
          cW,
          cropH
        );
        ctx.globalCompositeOperation = 'source-over';
      }
    }
  }, [drawFrame]);

  // Synchronize scrollProgress with frame sequence mapping
  useEffect(() => {
    // Phase 1: Hero Section (scroll <= 0.04)
    // Hold at frame 47 (ezgif-frame-048.jpg) once intro has finished playing
    if (scrollProgress <= 0.04) {
      if (heroIntroCompleteRef.current) {
        targetFrameRef.current = 47;
      }
      return;
    }

    // User has started scrolling past Hero:
    if (!heroIntroCompleteRef.current) {
      heroIntroPlayingRef.current = false;
      heroIntroCompleteRef.current = true;
      setIntroComplete(true);
      if (onHeroIntroComplete) {
        onHeroIntroComplete();
      }
    }

    // Check if reached Final State (scrollProgress >= 0.88)
    if (scrollProgress >= 0.88) {
      targetFrameRef.current = 239; // Final frame 240
      return;
    }

    // Scrollytelling Phases across frames 049 to 240 (indices 48 to 239):
    // Phase 2 — Disassembly: Frames 049–085 (indices 48 to 84) -> scroll 0.04 to 0.26
    // Phase 3 — Exploded Technical View: Frames 086–140 (indices 85 to 139) -> scroll 0.26 to 0.48
    // Phase 4 — Network / Distribution: Frames 141–190 (indices 140 to 189) -> scroll 0.48 to 0.70
    // Phase 5 — Final Assembly: Frames 191–240 (indices 190 to 239) -> scroll 0.70 to 0.88

    if (scrollProgress < 0.26) {
      const p = (scrollProgress - 0.04) / (0.26 - 0.04);
      targetFrameRef.current = 48 + p * (84 - 48);
    } else if (scrollProgress < 0.48) {
      const p = (scrollProgress - 0.26) / (0.48 - 0.26);
      targetFrameRef.current = 85 + p * (139 - 85);
    } else if (scrollProgress < 0.70) {
      const p = (scrollProgress - 0.48) / (0.70 - 0.48);
      targetFrameRef.current = 140 + p * (189 - 140);
    } else {
      const p = (scrollProgress - 0.70) / (0.88 - 0.70);
      targetFrameRef.current = 190 + p * (239 - 190);
    }
  }, [scrollProgress, onHeroIntroComplete]);

  // Main 60fps Render & Animation Loop
  useEffect(() => {
    let lastTime = performance.now();

    const loop = (time) => {
      const delta = Math.min((time - lastTime) / 1000, 0.1);
      lastTime = time;

      // ----------------------------------------------------------------------
      // CASE 1A: Initial Page Load — Play Hero Intro (Frames 001–048) ONCE
      // ----------------------------------------------------------------------
      if (heroIntroPlayingRef.current && scrollProgress <= 0.04) {
        // Advance at a smooth cinematic ~25fps rate from frame 0 to frame 47 (ezgif-frame-048.jpg)
        currentFrameRef.current += delta * 25;

        // When frame 47 (frame 048) is reached, complete intro and hold state
        if (currentFrameRef.current >= 47) {
          currentFrameRef.current = 47;
          heroIntroPlayingRef.current = false;
          heroIntroCompleteRef.current = true;
          targetFrameRef.current = 47;
          setIntroComplete(true);
          if (onHeroIntroComplete) {
            onHeroIntroComplete();
          }
        }

        drawFrame(currentFrameRef.current);
      }

      // ----------------------------------------------------------------------
      // CASE 1B: Hero Section Idle State (scrollProgress <= 0.04 and intro finished)
      // Continuously rotate 3D container inside the logo emblem using MODELFORGE_FRAMES2
      // ----------------------------------------------------------------------
      else if (scrollProgress <= 0.04) {
        heroIdleLoopTimeRef.current = (heroIdleLoopTimeRef.current + delta * 24) % Math.max(1, FRAME2_URLS.length);
        drawHeroIdleComposite(heroIdleLoopTimeRef.current);
      }

      // ----------------------------------------------------------------------
      // CASE 2: Final State (scrollProgress >= 0.88)
      // Run MODELFORGE_FRAMES1 animation continuously in place of current loop
      // ----------------------------------------------------------------------
      else if (scrollProgress >= 0.88) {
        // Continuous smooth loop through all 204 frames of MODELFORGE_FRAMES1 at 24fps
        finalLoopTimeRef.current = (finalLoopTimeRef.current + delta * 24) % Math.max(1, FRAME1_URLS.length);
        drawFrame1(finalLoopTimeRef.current);
      }

      // ----------------------------------------------------------------------
      // CASE 3: Active Scroll Journey (Frames 049–240)
      // Smooth lerp damping as user scrolls through disassembly, exploded view, network & reassembly
      // ----------------------------------------------------------------------
      else {
        const lerpFactor = 0.095;
        const diff = targetFrameRef.current - currentFrameRef.current;
        currentFrameRef.current += diff * lerpFactor;
        drawFrame(currentFrameRef.current);
      }

      animationFrameIdRef.current = requestAnimationFrame(loop);
    };

    animationFrameIdRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animationFrameIdRef.current);
  }, [drawFrame, drawFrame1, drawHeroIdleComposite, scrollProgress, onHeroIntroComplete]);

  // Responsive Canvas Sizing (Preserves 16:9 aspect ratio and high DPI)
  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.parentElement?.getBoundingClientRect();
      const width = Math.round(
        rect?.width || canvas.parentElement?.clientWidth || (window.innerWidth <= 600 ? Math.min(320, window.innerWidth * 0.88) : 640)
      );
      const height = Math.round(
        rect?.height || canvas.parentElement?.clientHeight || (width * 9) / 16
      );

      canvas.width = Math.max(1, width * dpr);
      canvas.height = Math.max(1, height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      if (scrollProgress <= 0.04 && heroIntroCompleteRef.current) {
        drawHeroIdleComposite(heroIdleLoopTimeRef.current);
      } else if (scrollProgress >= 0.88) {
        drawFrame1(finalLoopTimeRef.current);
      } else {
        drawFrame(currentFrameRef.current);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    window.addEventListener('orientationchange', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', handleResize);
    };
  }, [drawFrame, drawFrame1, drawHeroIdleComposite, scrollProgress]);

  // Determine Side-by-Side Spatial Alignment class (Anime.js Architecture)
  // Section 00 (Hero): RIGHT (Editorial Left | 3D Right)
  // Section 01 (Unpack): RIGHT (Editorial Left | 3D Right)
  // Section 02 (Container): LEFT (3D Left | Editorial Right)
  // Section 03 (Share): RIGHT (Editorial Left | 3D Right)
  // Section 04 (Impact): LEFT (3D Left | Editorial Right)
  // Section CTA (Final State): RIGHT (Editorial Left | 3D Right — Zero Overlap)
  const getSpatialAlignmentClass = () => {
    // Initial Hero Intro: 3D model sits centered in viewport while playing frames 001-048
    if (!introComplete && scrollProgress <= 0.04) {
      return 'stage-align-center';
    }
    if (scrollProgress >= 0.82 || activeChapter >= 5) {
      return 'stage-align-right';
    }
    switch (activeChapter) {
      case 2: // Section 02: 3D Model Left | Editorial Content Right
        return 'stage-align-left';
      case 4: // Section 04: 3D Model Left | Editorial Content Right
        return 'stage-align-left';
      default: // Hero, Section 01, Section 03, CTA: 3D Model Right | Editorial Content Left
        return 'stage-align-right';
    }
  };

  // Chapter-specific dynamic atmospheric bloom
  const getAtmosphereClass = () => {
    switch (activeChapter) {
      case 1:
        return 'atmosphere-amber';
      case 2:
        return 'atmosphere-cyan-subtle';
      case 3:
        return 'atmosphere-indigo';
      case 4:
        return 'atmosphere-cosmic';
      default:
        return 'atmosphere-cyan-soft';
    }
  };

  const isFinal = scrollProgress >= 0.88;
  const isHero = scrollProgress <= 0.04;

  return (
    <div className={`centered-3d-sticky-stage ${getSpatialAlignmentClass()}`} aria-hidden="true">
      {/* 3D Canvas Container seamlessly merging into the pure #000000 black page */}
      <div className="stage-canvas-frame">
        <canvas ref={canvasRef} className="stage-3d-canvas" />
      </div>
    </div>
  );
}
