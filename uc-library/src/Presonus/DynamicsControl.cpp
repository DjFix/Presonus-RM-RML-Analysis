#include "presonus/DynamicsControl.hpp"

#include "core/portable/gui/coreviewcontroller.h"
#include "core/system/coretime.h"

#include <cmath>
#include <limits>

namespace Presonus {
namespace {

int truncateCoordinate(float value) {
  if (std::isnan(value))
    return 0;
  if (value >= static_cast<float>(std::numeric_limits<int>::max()))
    return std::numeric_limits<int>::max();
  if (value <= static_cast<float>(std::numeric_limits<int>::min()))
    return std::numeric_limits<int>::min();
  return static_cast<int>(value);
}

} // namespace

using Core::Portable::Parameter;

DynamicsControl::DynamicsControl(Core::RectRef size)
    : Control(size, nullptr), vertical_(0.f, 1.f), horizontal_(0.f, 1.f) {}

DynamicsControl::~DynamicsControl() {
  for (auto *aux : {expander_, ratio_, threshold_})
    if (aux)
      aux->removeObserver(this);
}

void DynamicsControl::configureSourcePort(
    Mode mode, Core::Portable::ViewController *resolver) {
  mode_ = mode;
  resolver_ = resolver;
}

void DynamicsControl::calculatePivotPoints(int &x, int &y, int &gateEnd,
                                           int &compressorEnd) {
  Core::Rect bounds;
  getClientRect(bounds);
  const float normalized = threshold_ ? threshold_->getNormalized() : 0.f;
  const float xPosition = horizontal_.normalizedToRange(normalized);
  const float yPosition = static_cast<float>(bounds.getHeight()) -
                          vertical_.normalizedToRange(normalized);
  int gate = 0;
  int compressor = 0;
  if (mode_ == Mode::Gate) {
    const bool expanded = expander_ && expander_->getValue() > 0.f;
    gate = truncateCoordinate(expanded ? xPosition - 10.f : xPosition);
  } else if (mode_ == Mode::Compressor && ratio_ && yPosition > 0.f) {
    compressor = truncateCoordinate(yPosition - yPosition / ratio_->getValue());
  }
  x = truncateCoordinate(xPosition);
  y = truncateCoordinate(yPosition);
  gateEnd = gate;
  compressorEnd = compressor;
}

void DynamicsControl::onIdle() {
  Control::onIdle();
  const auto now = Core::SystemClock::getMilliseconds();
  if (now - lastInvalidate_ > 99 && pendingInvalidate_) {
    invalidate();
    lastInvalidate_ = now;
    pendingInvalidate_ = false;
  }
}

bool DynamicsControl::onTouchInput(const Core::Portable::TouchEvent &event) {
  if (!parameter || !isEnabled())
    return false;
  if (event.type == Core::Portable::TouchEvent::kDown)
    parameter->setValue(parameter->getValue() == 0.f ? 1.f : 0.f, true);
  return true;
}

void DynamicsControl::paramChanged(Parameter *changed, int message) {
  if (message == Parameter::kDestroyed) {
    // The current provider's Control callback excludes kDestroyed.
    if (changed == parameter) {
      setParameter(nullptr);
    } else {
      changed->removeObserver(this);
      if (threshold_ == changed)
        threshold_ = nullptr;
      else if (expander_ == changed)
        expander_ = nullptr;
      else if (ratio_ == changed)
        ratio_ = nullptr;
    }
    return;
  }
  if (message == Parameter::kChanged) {
    std::array<int, 4> pivots;
    calculatePivotPoints(pivots[0], pivots[1], pivots[2], pivots[3]);
    if (pivots != drawnPivots_)
      pendingInvalidate_ = true;
  }
  Control::paramChanged(changed, message);
}

void DynamicsControl::setSize(Core::RectRef size) {
  View::setSize(size);
  horizontal_.setRange(0.f, static_cast<float>(size.getWidth()), 1.f);
  vertical_.setRange(0.f, static_cast<float>(size.getHeight()), 1.f);
}

void DynamicsControl::draw(const Core::Portable::DrawEvent &event) {
  using Core::Point;
  using Core::Portable::BitmapPainter;

  if (auto *bitmap = background_.getBitmap())
    BitmapPainter::draw(event.graphics, Point(), *bitmap);

  Core::Rect client;
  getClientRect(client);
  auto &[x, y, gate, compressor] = drawnPivots_;
  calculatePivotPoints(x, y, gate, compressor);

  const bool active = !parameter || parameter->getValue() > 0.f;
  const auto color = active ? getStyle().getForeColor() : offLineColor_;
  event.graphics.drawLine(Point(x, y), Point(gate, client.getHeight()), color);
  event.graphics.drawLine(Point(x, y), Point(client.getWidth(), compressor),
                          color);
  if (active) {
    event.graphics.drawLine(Point(x + 1, y),
                            Point(gate + 1, client.getHeight()), color);
    event.graphics.drawLine(Point(x, y + 1),
                            Point(client.getWidth(), compressor + 1), color);
  }
  if (auto *bitmap = handle_.getBitmap()) {
    const int offset = bitmap->getWidth() / 2;
    const int frame = !active && bitmap->getFrameCount() > 1 ? 1 : 0;
    BitmapPainter::draw(event.graphics, Point(x - offset, y - offset), *bitmap,
                        frame);
  }
}

void DynamicsControl::setAttributes(
    const Core::Portable::Attributes &attributes) {
  using namespace Core::Portable;
  View::setAttributes(attributes);
  background_ = ViewAttributes::getBitmap(attributes, "image");
  Core::Rect bounds = getSize();
  if ((bounds.getWidth() <= 0 || bounds.getHeight() <= 0) &&
      ViewAttributes::autoSizeToBitmap(bounds, background_.getBitmap()))
    setSize(bounds);
  handle_ = ViewAttributes::getBitmap(attributes, "handle");
  offLineColor_ = ViewAttributes::getColor(attributes, "offLineColor",
                                           getStyle().getForeColor());

  if (!resolver_)
    return;
  const auto *params = attributes.getAttributes("params");
  if (!params)
    return;
  const auto resolve = [this, params](Core::CStringPtr key,
                                      Parameter *current) {
    const auto name = params->getString(key);
    return name && *name ? static_cast<Parameter *>(
                               resolver_->getObjectForView(name, kParamType))
                         : current;
  };
  const auto bind = [this](Parameter *&current, Parameter *resolved) {
    if (current == resolved)
      return;
    if (current)
      current->removeObserver(this);
    current = resolved;
    if (current)
      current->addObserver(this);
  };
  auto *expander = resolve("expander", expander_);
  auto *ratio = resolve("ratio", ratio_);
  auto *threshold = resolve("threshold", threshold_);
  bind(expander_, expander);
  bind(ratio_, ratio);
  bind(threshold_, threshold);
}

} // namespace Presonus
