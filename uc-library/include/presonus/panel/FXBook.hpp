#pragma once
#include "presonus/panel/Book.hpp"
namespace Core::Portable {
class Parameter;
}
namespace presonus::panel {
struct FXBookInspector;
}
namespace Presonus::Panel {
class FxPresetComponent;
// Partial portable source model. Public Book inheritance and storage are source
// choices supported by the observed base-constructor call, not recovered ABI.
// Both pointers are borrowed identities; construction never dereferences them.
class FXBook : public Book {
public:
  FXBook(int initialValue, FxPresetComponent *presetComponent,
         Core::Portable::Parameter *parameter);

private:
  friend struct presonus::panel::FXBookInspector;
  FxPresetComponent *presetComponent_;
  Core::Portable::Parameter *parameter_;
};
} // namespace Presonus::Panel
namespace presonus::panel {
// Independent inspection API, not an original interface.
struct FXBookInspector {
  static Presonus::Panel::FxPresetComponent *
  preset(const Presonus::Panel::FXBook &book) {
    return book.presetComponent_;
  }
  static Core::Portable::Parameter *
  parameter(const Presonus::Panel::FXBook &book) {
    return book.parameter_;
  }
};
} // namespace presonus::panel
