#include "presonus/MeterControl.hpp"
#include <algorithm>

namespace {
Core::Rect joined(const Core::Rect &a, const Core::Rect &b) {
  return {std::min(a.left, b.left), std::min(a.top, b.top),
          std::max(a.right, b.right), std::max(a.bottom, b.bottom)};
}
bool nonempty(const Core::Rect &r) {
  return r.right > r.left && r.bottom > r.top;
}
// Preserve the native short-circuit intersection, including inverted
// rectangles.
void clipNative(Core::Rect &r, const Core::Rect &clip) {
  r.left = std::max(r.left, clip.left);
  r.right = std::min(r.right, clip.right);
  if (r.left < r.right) {
    r.top = std::max(r.top, clip.top);
    r.bottom = std::min(r.bottom, clip.bottom);
  }
}
} // namespace

namespace Presonus {
bool MeterControl::portableIsVertical() const {
  return getSize().getHeight() > getSize().getWidth();
}

int MeterControl::normalizedToPixel(float v) const {
  if (!interpolator)
    return 0;
  if (reverse)
    v = 1.f - v;
  float mapped = interpolator->normalizedToRange(v);
  if (reverse)
    mapped = 1.f - mapped;
  const int extent =
      portableIsVertical() ? getSize().getHeight() : getSize().getWidth();
  return static_cast<int>(static_cast<float>(extent) * mapped);
}

Core::Rect MeterControl::getLitRect(float v) const {
  Core::Rect r;
  getClientRect(r);
  const int p = normalizedToPixel(v);
  if (portableIsVertical()) {
    if (reverse)
      r.bottom = p;
    else
      r.top = r.bottom - p;
  } else if (reverse)
    r.left = r.right - p;
  else
    r.right = p;
  return r;
}

Core::Rect MeterControl::getPeakRect(float v) const {
  Core::Rect r;
  getClientRect(r);
  const int p = normalizedToPixel(v);
  if (portableIsVertical()) {
    if (reverse) {
      r.top = p - 1;
      r.bottom = p;
    } else {
      r.top = r.bottom - p;
      r.bottom = r.top + 1;
    }
  } else if (reverse) {
    r.left = r.right - p;
    r.right = r.left + 1;
  } else {
    r.left = p - 1;
    r.right = p;
  }
  return r;
}

Core::Rect MeterControl::subtractRect(const Core::Rect &a,
                                      const Core::Rect &b) const {
  Core::Rect r = a;
  if (portableIsVertical()) {
    int top = b.top, bottom = b.bottom;
    if (b.getHeight() > a.getHeight()) {
      r = b;
      top = a.top;
      bottom = a.bottom;
    }
    if (reverse)
      r.top = bottom;
    else
      r.bottom = top;
  } else {
    int left = b.left, right = b.right;
    if (b.getWidth() > a.getWidth()) {
      r = b;
      left = a.left;
      right = a.right;
    }
    if (reverse)
      r.right = left;
    else
      r.left = right;
  }
  return r;
}

void MeterControl::setValue(float v) {
  if (drawnValue == v)
    return;
  value = v;
  if (immediate) {
    invalidate();
    return;
  }
  const Core::Rect oldRect = getLitRect(drawnValue);
  const Core::Rect newRect = getLitRect(value);
  valueDirty = subtractRect(oldRect, newRect);
}

void MeterControl::setPeakValue(float v) {
  if (drawnPeak == v)
    return;
  peak = v;
  if (immediate) {
    invalidate();
    return;
  }
  const Core::Rect oldRect = getPeakRect(drawnPeak);
  const Core::Rect newRect = getPeakRect(peak);
  peakDirty = joined(oldRect, newRect);
}

void MeterControl::setPeakParameter(Core::Portable::Parameter *p) {
  if (p == peakParameter)
    return;
  if (peakParameter)
    peakParameter->removeObserver(this);
  peakParameter = p;
  if (p)
    p->addObserver(this);
}

void MeterControl::paramChanged(Core::Portable::Parameter *p, int msg) {
  if (msg == Core::Portable::Parameter::kChanged) {
    if (p == parameter) {
      enable(p->isEnabled());
      setValue(p->getNormalized());
      return;
    }
    if (p == peakParameter) {
      setPeakValue(p->getNormalized());
      return;
    }
  }
  Control::paramChanged(p, msg);
}

void MeterControl::onIdle() {
  Control::onIdle();
  const bool p = nonempty(peakDirty);
  const bool v = nonempty(valueDirty);
  if (!p && !v)
    return;
  Core::Rect update = v ? valueDirty : peakDirty;
  if (p && v) {
    peakDirty = joined(peakDirty, valueDirty);
    update = peakDirty;
  }
  invalidate(update);
  valueDirty = Core::Rect();
  peakDirty = Core::Rect();
}

void MeterControl::draw(const Core::Portable::DrawEvent &e) {
  Core::Rect background;
  getClientRect(background);
  // Intentional CCL style adaptation: native word offsets 0, 4, 0x10
  // are supplied as semantic background/foreground/text colors. The original
  // Style member declarations and cross-version semantic mapping are
  // unresolved.
  const auto &s = getStyle();
  if (!immediate)
    clipNative(background, e.updateRect);
  e.graphics.fillRect(background, s.getBackColor());
  Core::Rect lit = getLitRect(value);
  if (!immediate)
    clipNative(lit, e.updateRect);
  e.graphics.fillRect(lit, s.getForeColor());
  if (!hidePeak) {
    Core::Rect peakRect = getPeakRect(peak);
    if (!immediate)
      clipNative(peakRect, e.updateRect);
    e.graphics.fillRect(peakRect, s.getTextColor());
  }
  drawnValue = value;
  drawnPeak = peak;
}
} // namespace Presonus
