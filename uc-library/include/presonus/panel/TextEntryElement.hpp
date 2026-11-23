#pragma once

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
};
} // namespace presonus::panel::portable

namespace Presonus::Panel {
class FieldElement;
// The portable constructor owns its Field and text state by composition.
// Original layout and unencoded return declarations remain unresolved.
class TextEntryElement {
public:
  TextEntryElement(int x, int y, const char *parameterName);
  TextEntryElement(const TextEntryElement &) = default;
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
  struct OwnedState;
  std::shared_ptr<OwnedState> owned_;
  presonus::panel::portable::TextEntryState *state_;
  FieldElement *field_ = nullptr;
};
} // namespace Presonus::Panel
