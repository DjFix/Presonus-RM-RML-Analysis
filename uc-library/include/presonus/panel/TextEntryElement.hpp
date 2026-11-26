#pragma once

#include "core/portable/coreparams.h"
#include "presonus/panel/ElementInfo.hpp"
#include "presonus/surface_panel/IDisplay.hpp"
#include <array>
#include <memory>

namespace Core::Portable {
class Parameter;
}

namespace presonus::panel::portable {
// Independent state for the observed cursor range of 0 through 32.
struct TextEntryState {
  unsigned cursor = 0;
  bool dirty = false;
  std::array<char, 32> text{};
  int encoderRemainder = 0;
};
} // namespace presonus::panel::portable

namespace Presonus::Panel {
class FieldElement;
// The portable constructor owns its Field and text state by composition.
// Original layout and unencoded return declarations remain unresolved.
class TextEntryElement : private Core::Portable::ParamObserverBase {
public:
  TextEntryElement(int x, int y, const char *parameterName);
  explicit TextEntryElement(const ElementInfo &info);
  TextEntryElement(const TextEntryElement &other);
  virtual ~TextEntryElement();
  char getChar(int index);
  char getCurrentChar();
  void setCurrentChar(char character);
  bool deltaEncoder(int delta);
  bool tap();
  bool next();
  virtual void getDrawString(Core::CString128 &buffer, unsigned int flags);
  virtual void render(IDisplay &display, bool force);
  virtual void draw(IDisplay &display);
  void paramChanged(Core::Portable::Parameter *parameter, int message) override;
  TextEntryElement &operator=(const TextEntryElement &) = delete;

  explicit TextEntryElement(presonus::panel::portable::TextEntryState &state)
      : state_(&state) {}

  TextEntryElement(presonus::panel::portable::TextEntryState &state,
                   FieldElement &field)
      : state_(&state), field_(&field) {}

  void setString(const char *text);
  const presonus::panel::portable::TextEntryState &textState() const {
    return *state_;
  }
  const FieldElement *fieldElement() const { return field_; }

  // The role-wide binding borrows a live parameter; clear it before
  // destruction.
  static void setEncoderParam(Core::Portable::Parameter *parameter);
  Core::Portable::Parameter *getParam();
  Core::Portable::Parameter *getInternalParam();
  bool previous();

private:
  void markDirty();
  Core::Portable::Parameter *observed_ = nullptr;
  struct OwnedState;
  std::shared_ptr<OwnedState> owned_;
  presonus::panel::portable::TextEntryState *state_;
  FieldElement *field_ = nullptr;
};
} // namespace Presonus::Panel
