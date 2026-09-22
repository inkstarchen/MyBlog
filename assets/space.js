(() => {
  "use strict";

  const dataElement = document.getElementById("space-data");
  if (!dataElement) return;

  const graph = JSON.parse(dataElement.textContent);
  const nodes = graph.nodes;
  const stage = document.getElementById("space-stage");
  const orbit = document.getElementById("orbit");
  const core = document.getElementById("core");
  const coreCopy = core.querySelector(".core-copy");
  const coreTitle = document.getElementById("core-title");
  const coreDescription = document.getElementById("core-description");
  const depthLabel = document.getElementById("depth-label");
  const backSlot = document.getElementById("back-slot");
  const breadcrumbs = document.querySelector(".breadcrumbs");
  const contentPanel = document.getElementById("content-panel");
  const articleBody = document.getElementById("article-body");
  const readingScrollbar = document.getElementById("reading-scrollbar");
  const readingThumb = document.getElementById("reading-thumb");
  const spaceHint = document.getElementById("space-hint");
  const status = document.getElementById("space-status");
  const motionToggle = document.getElementById("motion-toggle");
  const scriptUrl = new URL(document.currentScript.src);
  const rootUrl = new URL("../", scriptUrl);
  const systemReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  let currentPath = document.body.dataset.currentPath || "";
  let particles = [];
  let animationFrame = 0;
  let previousTime = performance.now();
  let transitioning = false;
  let draggingScrollbar = false;
  let dragStartY = 0;
  let dragStartScrollTop = 0;
  let manualReducedMotion = localStorage.getItem("cognitive-space-reduced-motion") === "true";

  function prefersReducedMotion() {
    return manualReducedMotion || systemReducedMotion.matches;
  }

  async function fadeElements(elements, targetOpacity, duration) {
    const targets = elements.filter(Boolean);
    if (!targets.length) return;

    if (prefersReducedMotion()) {
      targets.forEach((element) => { element.style.opacity = String(targetOpacity); });
      return;
    }

    const animations = targets.map((element) => {
      const currentOpacity = Number.parseFloat(getComputedStyle(element).opacity);
      const easing = targetOpacity === 0
        ? "cubic-bezier(.45,.05,.3,1)"
        : "cubic-bezier(.16,1,.3,1)";
      return element.animate(
        [
          { opacity: Number.isFinite(currentOpacity) ? currentOpacity : 1 },
          { opacity: targetOpacity },
        ],
        { duration, easing, fill: "forwards" },
      );
    });

    await Promise.all(animations.map((animation) => animation.finished.catch(() => {})));
    targets.forEach((element) => { element.style.opacity = String(targetOpacity); });
    animations.forEach((animation) => animation.cancel());
  }

  function nodeUrl(path) {
    return new URL(path || "./", rootUrl).href;
  }

  function escapeText(value) {
    const span = document.createElement("span");
    span.textContent = value;
    return span.innerHTML;
  }

  function hash(value) {
    let result = 2166136261;
    for (let index = 0; index < value.length; index += 1) {
      result ^= value.charCodeAt(index);
      result = Math.imul(result, 16777619);
    }
    return result >>> 0;
  }

  function layoutFor(children) {
    const width = stage.clientWidth;
    const height = stage.clientHeight;
    const mobile = width < 720;
    const count = children.length;
    const maxRadius = Math.min(width * (mobile ? 0.38 : 0.37), height * (mobile ? 0.35 : 0.36));
    const minRadius = mobile ? 128 : 175;
    const outerRadius = Math.max(minRadius, maxRadius);
    const useTwoRings = count > (mobile ? 7 : 10);
    const phase = (hash(currentPath || "root") % 628) / 100;

    return children.map((child, index) => {
      const inner = useTwoRings && index % 2 === 0;
      const ringIndex = useTwoRings ? Math.floor(index / 2) : index;
      const ringCount = useTwoRings ? Math.ceil(count / 2) : count;
      const radius = inner ? outerRadius * 0.68 : outerRadius;
      const angle = phase + (Math.PI * 2 * ringIndex) / Math.max(ringCount, 1) + (inner ? 0.23 : 0);
      return {
        targetX: Math.cos(angle) * radius,
        targetY: Math.sin(angle) * radius * (mobile ? 1.08 : 0.72),
        angle,
      };
    });
  }

  function renderOrbit(entering = false) {
    const node = nodes[currentPath];
    const children = node.children.map((path) => nodes[path]);
    const layout = layoutFor(children);
    orbit.innerHTML = "";
    particles = [];

    if (!children.length) {
      const empty = document.createElement("p");
      empty.className = "empty-orbit";
      empty.textContent = "这里暂时没有更深的入口";
      orbit.appendChild(empty);
      return;
    }

    children.forEach((child, index) => {
      const anchor = document.createElement("a");
      anchor.className = "orbit-link";
      anchor.href = nodeUrl(child.path);
      anchor.dataset.spacePath = child.path;
      anchor.innerHTML = `<span>${escapeText(child.title)}</span>`;
      anchor.setAttribute("aria-label", `进入 ${child.title}`);
      orbit.appendChild(anchor);

      const seed = hash(child.path);
      const point = layout[index];
      particles.push({
        element: anchor,
        x: entering && !prefersReducedMotion() ? point.targetX * 0.12 : point.targetX,
        y: entering && !prefersReducedMotion() ? point.targetY * 0.12 : point.targetY,
        vx: 0,
        vy: 0,
        targetX: point.targetX,
        targetY: point.targetY,
        angle: point.angle,
        phase: (seed % 1000) / 85,
        amplitude: 4 + (seed % 7),
      });
      anchor.style.opacity = entering && !prefersReducedMotion() ? "0" : "1";
      if (entering && !prefersReducedMotion()) {
        anchor.animate(
          [{ opacity: 0 }, { opacity: 1 }],
          { duration: 620, delay: 130 + index * 45, easing: "ease-out", fill: "forwards" },
        );
      }
    });
  }

  function updateParticleTargets() {
    const node = nodes[currentPath];
    const children = node.children.map((path) => nodes[path]);
    const layout = layoutFor(children);
    particles.forEach((particle, index) => {
      if (!layout[index]) return;
      particle.targetX = layout[index].targetX;
      particle.targetY = layout[index].targetY;
      particle.angle = layout[index].angle;
    });
  }

  function tick(time) {
    const delta = Math.min((time - previousTime) / 16.67, 2);
    previousTime = time;
    const still = prefersReducedMotion();

    if (!transitioning) {
      particles.forEach((particle) => {
        const driftX = still ? 0 : Math.sin(time / 2100 + particle.phase) * particle.amplitude;
        const driftY = still ? 0 : Math.cos(time / 2700 + particle.phase * 1.3) * particle.amplitude * 0.7;
        const spring = 0.022 * delta;
        particle.vx += (particle.targetX + driftX - particle.x) * spring;
        particle.vy += (particle.targetY + driftY - particle.y) * spring;
        particle.vx *= Math.pow(0.84, delta);
        particle.vy *= Math.pow(0.84, delta);
        particle.x += particle.vx * delta;
        particle.y += particle.vy * delta;
        particle.element.style.transform = `translate(calc(-50% + ${particle.x}px), calc(-50% + ${particle.y}px))`;
      });
    }
    animationFrame = requestAnimationFrame(tick);
  }

  function breadcrumbChain(node) {
    const chain = [];
    let cursor = node;
    while (cursor) {
      chain.push(cursor);
      cursor = cursor.parent === null ? null : nodes[cursor.parent];
    }
    return chain.reverse();
  }

  function updateChrome() {
    const node = nodes[currentPath];
    const depth = currentPath.split("/").filter(Boolean).length;
    coreTitle.textContent = node.title;
    coreDescription.textContent = node.description;
    depthLabel.textContent = depth === 0 ? "起点" : `第 ${depth} 层`;
    articleBody.innerHTML = node.body;
    document.title = currentPath ? `${node.title} · ${graph.site.title}` : graph.site.title;
    document.body.dataset.currentPath = currentPath;

    backSlot.innerHTML = "";
    if (node.parent !== null) {
      const back = document.createElement("a");
      back.className = "back-link";
      back.href = nodeUrl(node.parent);
      back.dataset.spacePath = node.parent;
      back.setAttribute("aria-label", "返回上一级");
      back.innerHTML = '<span aria-hidden="true">←</span><span>返回</span>';
      backSlot.appendChild(back);
    }

    breadcrumbs.innerHTML = "";
    breadcrumbChain(node).forEach((item, index, chain) => {
      const link = document.createElement("a");
      link.href = nodeUrl(item.path);
      link.dataset.spacePath = item.path;
      link.textContent = item.title;
      breadcrumbs.appendChild(link);
      if (index < chain.length - 1) breadcrumbs.append(" / ");
    });
  }

  function currentIsLeaf() {
    return nodes[currentPath].children.length === 0;
  }

  function updateReadingScrollbar() {
    const trackHeight = readingScrollbar.clientHeight;
    const maximumScroll = Math.max(0, contentPanel.scrollHeight - contentPanel.clientHeight);
    const visibleRatio = Math.min(1, contentPanel.clientHeight / Math.max(contentPanel.scrollHeight, 1));
    const thumbHeight = maximumScroll === 0 ? trackHeight : Math.max(46, trackHeight * visibleRatio);
    const maximumTravel = Math.max(0, trackHeight - thumbHeight);
    const progress = maximumScroll === 0 ? 0 : contentPanel.scrollTop / maximumScroll;
    readingThumb.style.height = `${thumbHeight}px`;
    readingThumb.style.transform = `translate(-50%, ${maximumTravel * progress}px)`;
    readingScrollbar.setAttribute("aria-valuenow", String(Math.round(progress * 100)));
    readingScrollbar.classList.toggle("is-static", maximumScroll === 0);
  }

  function setReadingMode(open, options = {}) {
    document.body.classList.remove("reading-leaving");
    contentPanel.classList.remove("is-closing");
    readingScrollbar.classList.remove("is-closing");
    document.body.classList.toggle("reading-mode", open);
    contentPanel.classList.toggle("is-open", open);
    contentPanel.setAttribute("aria-hidden", String(!open));
    contentPanel.tabIndex = open ? 0 : -1;
    readingScrollbar.setAttribute("aria-hidden", String(!open));
    readingScrollbar.tabIndex = open ? 0 : -1;
    core.setAttribute("aria-expanded", String(open));
    spaceHint.textContent = open
      ? "上下滑动阅读 · 返回上一级可收起"
      : "选择一个主题，慢慢深入 · 点击中心阅读";
    if (options.reset) contentPanel.scrollTop = 0;
    if (open) {
      requestAnimationFrame(() => {
        updateReadingScrollbar();
        if (options.focus) contentPanel.focus({ preventScroll: true });
      });
    }
  }

  async function closeReadingMode(animated = false) {
    const wasOpen = document.body.classList.contains("reading-mode");
    if (!wasOpen || !animated || prefersReducedMotion()) {
      setReadingMode(false);
      return;
    }

    document.body.classList.add("reading-leaving");
    document.body.classList.remove("reading-mode");
    contentPanel.classList.remove("is-open");
    contentPanel.classList.add("is-closing");
    contentPanel.setAttribute("aria-hidden", "true");
    contentPanel.tabIndex = -1;
    readingScrollbar.classList.add("is-closing");
    readingScrollbar.setAttribute("aria-hidden", "true");
    readingScrollbar.tabIndex = -1;
    core.setAttribute("aria-expanded", "false");
    spaceHint.textContent = "选择一个主题，慢慢深入 · 点击中心阅读";

    await new Promise((resolve) => window.setTimeout(resolve, 1050));
    document.body.classList.remove("reading-leaving");
    contentPanel.classList.remove("is-closing");
    readingScrollbar.classList.remove("is-closing");
  }

  function syncReadingMode() {
    setReadingMode(currentIsLeaf(), { reset: true });
  }

  async function closeCurrentNote() {
    if (transitioning) return;
    transitioning = true;
    document.body.classList.add("orbit-held");
    await closeReadingMode(true);

    if (!prefersReducedMotion()) {
      await new Promise((resolve) => window.setTimeout(resolve, 1080));
    }

    document.body.classList.remove("orbit-held");
    status.textContent = `已收起${nodes[currentPath].title}的笔记`;
    transitioning = false;
  }

  async function navigate(path, options = {}) {
    if (transitioning || !Object.prototype.hasOwnProperty.call(nodes, path) || path === currentPath) return;
    const wasReading = document.body.classList.contains("reading-mode");
    transitioning = true;

    if (wasReading) {
      document.body.classList.add("orbit-held");
      await Promise.all([
        closeReadingMode(true),
        fadeElements([backSlot, breadcrumbs], 0, 900),
      ]);

      if (!prefersReducedMotion()) {
        await new Promise((resolve) => window.setTimeout(resolve, 1080));
      }

      await fadeElements([coreCopy], 0, 560);
      if (!prefersReducedMotion()) {
        await new Promise((resolve) => window.setTimeout(resolve, 120));
      }
      currentPath = path;
      updateChrome();
      syncReadingMode();
      if (!options.fromHistory) history.pushState({ path }, "", nodeUrl(path));

      await Promise.all([
        fadeElements([coreCopy], 1, 620),
        fadeElements([backSlot, breadcrumbs], 1, 720),
      ]);

      renderOrbit(true);
      document.body.classList.remove("orbit-held");
      status.textContent = `已返回${nodes[path].title}，第 ${path.split("/").filter(Boolean).length} 层`;
      transitioning = false;
      return;
    }

    await closeReadingMode(true);
    const oldParticles = [...particles];
    const duration = prefersReducedMotion() ? 1 : 560;

    oldParticles.forEach((particle, index) => {
      const distance = Math.max(stage.clientWidth, stage.clientHeight) * 0.75;
      const outX = particle.x + Math.cos(particle.angle) * distance;
      const outY = particle.y + Math.sin(particle.angle) * distance;
      particle.element.animate(
        [
          { transform: `translate(calc(-50% + ${particle.x}px), calc(-50% + ${particle.y}px))`, opacity: 1 },
          { transform: `translate(calc(-50% + ${outX}px), calc(-50% + ${outY}px))`, opacity: 0 },
        ],
        { duration, delay: prefersReducedMotion() ? 0 : index * 18, easing: "cubic-bezier(.3,.7,.2,1)", fill: "forwards" },
      );
    });
    core.animate(
      [{ transform: "translate(-50%, -50%) scale(1)" }, { transform: "translate(-50%, -50%) scale(.86)", opacity: 0.45 }],
      { duration: Math.max(1, duration * 0.72), direction: "alternate", iterations: 2, easing: "ease-in-out" },
    );

    await new Promise((resolve) => window.setTimeout(resolve, duration));
    currentPath = path;
    updateChrome();
    renderOrbit(true);
    syncReadingMode();
    document.body.classList.remove("orbit-held");
    if (!options.fromHistory) history.pushState({ path }, "", nodeUrl(path));
    status.textContent = `已进入${nodes[path].title}，第 ${path.split("/").filter(Boolean).length} 层`;
    transitioning = false;
  }

  document.addEventListener("click", (event) => {
    const link = event.target.closest("[data-space-path]");
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(link.dataset.spacePath);
  });

  core.addEventListener("click", () => {
    if (transitioning) return;
    if (document.body.classList.contains("reading-mode")) {
      if (currentIsLeaf()) contentPanel.focus({ preventScroll: true });
      else closeCurrentNote();
    } else {
      setReadingMode(true, { focus: true, reset: true });
    }
  });

  contentPanel.addEventListener("scroll", updateReadingScrollbar, { passive: true });
  readingScrollbar.addEventListener("pointerdown", (event) => {
    const rect = readingScrollbar.getBoundingClientRect();
    const maximumScroll = Math.max(0, contentPanel.scrollHeight - contentPanel.clientHeight);
    if (event.target === readingThumb) {
      draggingScrollbar = true;
      dragStartY = event.clientY;
      dragStartScrollTop = contentPanel.scrollTop;
      readingScrollbar.setPointerCapture(event.pointerId);
      return;
    }
    const progress = Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height));
    contentPanel.scrollTo({ top: maximumScroll * progress, behavior: prefersReducedMotion() ? "auto" : "smooth" });
  });
  readingScrollbar.addEventListener("pointermove", (event) => {
    if (!draggingScrollbar) return;
    const maximumScroll = Math.max(0, contentPanel.scrollHeight - contentPanel.clientHeight);
    const maximumTravel = Math.max(1, readingScrollbar.clientHeight - readingThumb.offsetHeight);
    contentPanel.scrollTop = dragStartScrollTop + ((event.clientY - dragStartY) / maximumTravel) * maximumScroll;
  });
  readingScrollbar.addEventListener("pointerup", () => { draggingScrollbar = false; });
  readingScrollbar.addEventListener("pointercancel", () => { draggingScrollbar = false; });
  readingScrollbar.addEventListener("keydown", (event) => {
    const steps = { ArrowDown: 72, ArrowUp: -72, PageDown: contentPanel.clientHeight * 0.82, PageUp: -contentPanel.clientHeight * 0.82 };
    if (Object.prototype.hasOwnProperty.call(steps, event.key)) {
      event.preventDefault();
      contentPanel.scrollBy({ top: steps[event.key], behavior: prefersReducedMotion() ? "auto" : "smooth" });
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      contentPanel.scrollTo({ top: event.key === "Home" ? 0 : contentPanel.scrollHeight, behavior: prefersReducedMotion() ? "auto" : "smooth" });
    }
  });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (document.body.classList.contains("reading-mode") && !currentIsLeaf()) closeReadingMode(true);
      else if (nodes[currentPath].parent !== null) navigate(nodes[currentPath].parent);
    }
  });

  window.addEventListener("popstate", (event) => {
    const path = event.state?.path;
    if (typeof path === "string" && Object.prototype.hasOwnProperty.call(nodes, path)) navigate(path, { fromHistory: true });
    else window.location.reload();
  });

  window.addEventListener("resize", () => {
    updateParticleTargets();
    updateReadingScrollbar();
  });
  motionToggle.addEventListener("click", () => {
    manualReducedMotion = !manualReducedMotion;
    localStorage.setItem("cognitive-space-reduced-motion", String(manualReducedMotion));
    document.body.classList.toggle("reduced-motion", manualReducedMotion);
    motionToggle.setAttribute("aria-pressed", String(manualReducedMotion));
    motionToggle.textContent = manualReducedMotion ? "恢复动态" : "减弱动态";
  });

  document.body.classList.toggle("reduced-motion", manualReducedMotion);
  motionToggle.setAttribute("aria-pressed", String(manualReducedMotion));
  motionToggle.textContent = manualReducedMotion ? "恢复动态" : "减弱动态";
  renderOrbit(false);
  syncReadingMode();
  history.replaceState({ path: currentPath }, "", window.location.href);
  animationFrame = requestAnimationFrame(tick);

  window.addEventListener("pagehide", () => cancelAnimationFrame(animationFrame), { once: true });
})();
