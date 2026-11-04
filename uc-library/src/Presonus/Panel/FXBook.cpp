#include "presonus/panel/FXBook.hpp"
namespace Presonus::Panel {
FXBook::FXBook(int initialValue, FxPresetComponent *presetComponent,
               Core::Portable::Parameter *parameter)
    : Book(initialValue), presetComponent_(presetComponent),
      parameter_(parameter) {}
} // namespace Presonus::Panel
