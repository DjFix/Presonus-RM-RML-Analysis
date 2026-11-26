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

  explicit OwnedState(const ElementInfo &info) : field(info) {
    text.dirty = true;
  }

  OwnedState(int x, int y, const char *parameterName)
      : field(x, y, parameterName) {
    text.dirty = field.needsToDraw();
  }
};

TextEntryElement::TextEntryElement(int x, int y, const char *parameterName)
    : owned_(std::make_shared<OwnedState>(x, y, parameterName)),
      state_(&owned_->text), field_(&owned_->field) {}

TextEntryElement::TextEntryElement(const ElementInfo &info)
    : owned_(std::make_shared<OwnedState>(info)), state_(&owned_->text),
      field_(&owned_->field) {}

TextEntryElement::TextEntryElement(const TextEntryElement &other)
    : owned_(other.owned_), state_(other.state_), field_(other.field_) {}

TextEntryElement::~TextEntryElement() {
  if (observed_)
    observed_->removeObserver(this);
  if (encoderParameter)
    encoderParameter->removeObserver(this);
}

void TextEntryElement::setEncoderParam(Core::Portable::Parameter *parameter) {
  if (encoderParameter != parameter)
    encoderParameter = parameter;
}

Core::Portable::Parameter *TextEntryElement::getParam() {
  return encoderParameter;
}

Core::Portable::Parameter *TextEntryElement::getInternalParam() {
  auto *parameter = field_ ? field_->getParam() : nullptr;
  if (parameter != observed_) {
    if (observed_)
      observed_->removeObserver(this);
    observed_ = parameter;
    if (observed_)
      observed_->addObserver(this);
  }
  return parameter;
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

namespace Presonus::Panel {
void TextEntryElement::markDirty() {
  state_->dirty = true;
  if (field_)
    field_->setDirty(1);
}

void TextEntryElement::getDrawString(Core::CString128 &buffer,
                                     unsigned int flags) {
  auto *parameter = getInternalParam();
  if (parameter) {
    field_->getDrawString(parameter, buffer, flags);
    if (buffer.isEmpty())
      if (auto *string = Core::Portable::StringParam::cast(parameter))
        buffer = string->getDefaultText();
  } else {
    buffer = state_->text.data();
  }
}

char TextEntryElement::getChar(int index) {
  Core::CString128 text;
  getDrawString(text, 32);
  // Negative native indices access outside the temporary buffer and are
  // excluded.
  return index >= 0 && index < text.length() ? text.str()[index] : ' ';
}

char TextEntryElement::getCurrentChar() {
  return state_->cursor <= 31 ? getChar(static_cast<int>(state_->cursor)) : ' ';
}

void TextEntryElement::setCurrentChar(char character) {
  if (state_->cursor > 31)
    return;
  Core::CString128 text;
  getDrawString(text, 32);
  const auto length = static_cast<unsigned>(text.length());
  if (state_->cursor > length) {
    state_->cursor = length;
    return;
  }
  std::string result(text.str(), state_->cursor);
  if (character)
    result += character;
  if (state_->cursor < length)
    result += text.str() + state_->cursor + 1;
  setString(result.c_str());
  markDirty();
}

bool TextEntryElement::tap() {
  if (state_->cursor <= 31) {
    setCurrentChar(' ');
    if (state_->cursor + 1 <= 31)
      ++state_->cursor;
  }
  return false;
}

bool TextEntryElement::next() {
  Core::CString128 text;
  getDrawString(text, 32);
  const auto old = state_->cursor;
  const auto next = old + 1;
  if (next > 31)
    return true;
  state_->cursor = next;
  const auto length = static_cast<unsigned>(text.length());
  if (next == length && getChar(static_cast<int>(old)) != ' ') {
    setCurrentChar(' ');
    return true;
  }
  if (next < length)
    markDirty();
  else
    state_->cursor = old;
  return true;
}

bool TextEntryElement::deltaEncoder(int delta) {
  // Explicit wrapping models ARM add without signed host overflow.
  state_->encoderRemainder = static_cast<std::int32_t>(
      static_cast<std::uint32_t>(state_->encoderRemainder) +
      static_cast<std::uint32_t>(delta));
  const int accumulated = state_->encoderRemainder;
  if (accumulated >= -1 && accumulated <= 1)
    return true;
  state_->encoderRemainder = 0;
  const int steps = accumulated / 2;
  const unsigned char current = static_cast<unsigned char>(getCurrentChar());
  unsigned char value;
  if (current == ' ' && steps > 0)
    value = state_->cursor > 0 &&
                    getChar(static_cast<int>(state_->cursor - 1)) > '@'
                ? 'a'
                : 'A';
  else if (current == 'A' && steps < 0)
    value = ' ';
  else {
    value =
        static_cast<unsigned char>(current + static_cast<std::uint32_t>(steps));
    if (value <= 31)
      value = ' ';
    else if (value > 126)
      value = '!';
    else if (value == '.')
      value = steps > 0 ? '/' : '-';
  }
  setCurrentChar(static_cast<char>(value));
  return true;
}

void TextEntryElement::paramChanged(Core::Portable::Parameter *parameter,
                                    int message) {
  if (message == Core::Portable::Parameter::kDestroyed) {
    parameter->removeObserver(this);
    if (parameter == observed_)
      observed_ = nullptr;
  }
  if (field_ && parameter == field_->cachedParameter())
    markDirty();
}

void TextEntryElement::draw(IDisplay &display) {
  render(display, field_ && field_->elementState().activation != 0);
}

void TextEntryElement::render(IDisplay &display, bool force) {
  Core::CString128 text;
  getDrawString(text, 32);
  if (field_)
    field_->renderText(display, false, text);
  state_->dirty = false;
  getDrawString(text, 32);
  if (state_->cursor < static_cast<unsigned>(text.length()))
    text.getBuffer()[state_->cursor] = 0;
  const int prefixWidth = display.pixelLength(text);
  char character[2] = {getCurrentChar(), 0};
  const int width = display.pixelLength(character);
  const int height = display.getTextBoxHeight();
  const int x = field_ ? field_->elementState().x : 0;
  const int y = field_ ? field_->elementState().y : 0;
  if (force)
    display.invertRect({x - 1 + prefixWidth, y - 1, width + 1, height});
}
} // namespace Presonus::Panel
