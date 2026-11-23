#include "presonus/panel/TextEntryElement.hpp"

#include "presonus/panel/FieldElement.hpp"

#include <algorithm>
#include <cstring>

namespace Presonus::Panel {
namespace {
Core::Portable::Parameter *encoderParameter = nullptr;
}

struct TextEntryElement::OwnedState {
  FieldElement field;
  presonus::panel::portable::TextEntryState text;

  OwnedState(int x, int y, const char *parameterName)
      : field(x, y, parameterName) {
    text.dirty = field.needsToDraw();
  }
};

TextEntryElement::TextEntryElement(int x, int y, const char *parameterName)
    : owned_(std::make_shared<OwnedState>(x, y, parameterName)),
      state_(&owned_->text), field_(&owned_->field) {}

void TextEntryElement::setEncoderParam(Core::Portable::Parameter *parameter) {
  if (encoderParameter != parameter)
    encoderParameter = parameter;
}

Core::Portable::Parameter *TextEntryElement::getParam() {
  return encoderParameter;
}

Core::Portable::Parameter *TextEntryElement::getInternalParam() {
  return field_ ? field_->getParam() : nullptr;
}

void TextEntryElement::setString(const char *text) {
  if (field_ && field_->getParam()) {
    field_->getParam()->fromString(text, false);
  } else {
    state_->text.front() = '\0';
    const auto length =
        text ? std::min(std::strlen(text), state_->text.size() - 1) : 0;
    if (length)
      std::memmove(state_->text.data(), text, length);
    state_->text[length] = '\0';
  }
  state_->dirty = true;
  if (owned_)
    owned_->field.setDirty(1);
}

bool TextEntryElement::previous() {
  if (state_->cursor == 0)
    return false;
  --state_->cursor;
  state_->dirty = true;
  if (owned_)
    owned_->field.setDirty(1);
  return true;
}
} // namespace Presonus::Panel
