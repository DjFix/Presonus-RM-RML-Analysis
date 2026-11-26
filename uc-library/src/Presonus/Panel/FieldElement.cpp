#include "presonus/panel/FieldElement.hpp"

#include "core/portable/coresingleton.h"
#include "presonus/panel/LCDManager.hpp"

#include <algorithm>
#include <cstring>
#include <utility>

namespace Presonus::Panel {
namespace {
class DefaultFieldLookup
    : public Core::Portable::Singleton<DefaultFieldLookup> {
public:
  LCDManager manager{LCDManager::SourcePortConstruction{}};
};
} // namespace
} // namespace Presonus::Panel

DEFINE_SINGLETON(Presonus::Panel::DefaultFieldLookup)

namespace Presonus::Panel {
FieldElement::FieldElement(const ElementInfo &info)
    : OffscreenElement(info), parameterName_(info.name()), textBuffer_(nullptr),
      manager_(nullptr), refreshParameter_(info.observation[93] != 0) {}

FieldElement::FieldElement(int x, int y, const char *parameterName)
    : OffscreenElement(x, y),
      parameterName_(parameterName ? parameterName : ""), textBuffer_(nullptr),
      manager_(nullptr) {
  lookupParameters();
}

FieldElement::FieldElement(std::string parameterName, LCDManager *manager)
    : OffscreenElement(0, 0), parameterName_(std::move(parameterName)),
      manager_(manager) {}

FieldElement::~FieldElement() {
  if (parameter_)
    parameter_->removeObserver(this);
}

bool FieldElement::needsToDraw() const { return Element::needsToDraw(); }

LCDManager &FieldElement::defaultLookupManager() {
  return DefaultFieldLookup::instance().manager;
}

void FieldElement::lookupParameters() {
  LCDManager &manager = manager_ ? *manager_ : defaultLookupManager();
  auto *resolved = manager.lookupElementParameter(parameterName_.c_str());
  if (resolved == parameter_)
    return;
  if (parameter_)
    parameter_->removeObserver(this);
  parameter_ = resolved;
  if (parameter_)
    parameter_->addObserver(this);
  setDirty(1);
}

Core::Portable::Parameter *FieldElement::getParam() {
  if (!parameter_ || refreshParameter_)
    lookupParameters();
  return parameter_;
}

void FieldElement::getDrawString(const Core::Portable::Parameter *parameter,
                                 Core::CString128 &buffer, unsigned int flags) {
  // The original Parameter vtable +0x20/+0x70 resolves to isEnabled/toString
  // (char*, int). The application buffer has 128 bytes; oversized requests are
  // bounded intentionally in this portable API.
  if (parameter && parameter->isEnabled())
    parameter->toString(buffer.getBuffer(),
                        static_cast<int>(std::min(flags, 128u)));
  else
    buffer.empty();
}

void FieldElement::getDrawString(Core::CString128 &buffer, unsigned int flags) {
  if (refreshParameter_)
    lookupParameters();
  getDrawString(getParam(), buffer, flags);
}

void FieldElement::render(IDisplay &display, bool force) {
  setDirty(0);
  Core::CString128 text;
  getDrawString(text, 32);
  renderText(display, force, text);
}

void FieldElement::renderText(IDisplay &display, bool force,
                              const Core::CString128 &text) {
  setDirty(0);
  const bool invert = force && !text.isEmpty();
  const auto &state = elementState();
  display.moveTo(state.x, state.y);
  auto &current = drawingBounds();
  if (current.width <= 0 || current.height <= 0 ||
      std::strcmp(textBuffer_.str(), text.str()) != 0)
    display.drawString(text, sourceInfo().word(12), &current);
  if (current.width > 0 && current.height > 0) {
    textBuffer_ = text;
    Rectangle clear = previousBounds_;
    if (clear.width <= 0 || clear.height <= 0)
      clear = current;
    else if (clear.width < current.width)
      clear.width = current.width;
    const int color = sourceInfo().word(84);
    display.setTextColor(color);
    if (color == 0 || color == 1) {
      if (color == 0)
        display.eraseRect(clear);
      else
        display.fillRect(clear);
      display.moveTo(state.x, state.y);
      display.drawString(text, sourceInfo().word(12), nullptr);
    }
    if (invert)
      display.invertRect(current);
  } else if (previousBounds_.width > 0 && previousBounds_.height > 0) {
    const int color = sourceInfo().word(84);
    if (color == 0)
      display.eraseRect(previousBounds_);
    else if (color == 1)
      display.fillRect(previousBounds_);
  }
  previousBounds_ = current;
}

void FieldElement::paramChanged(Core::Portable::Parameter *parameter,
                                int message) {
  if (parameter == parameter_ &&
      message == Core::Portable::Parameter::kDestroyed)
    parameter_ = nullptr;
}
} // namespace Presonus::Panel
