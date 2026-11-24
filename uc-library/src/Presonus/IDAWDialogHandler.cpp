#include "presonus/IDAWDialogHandler.hpp"

namespace Presonus {

IDAWDialogHandler::DialogMenu::DialogMenu() = default;
IDAWDialogHandler::DialogMenu::~DialogMenu() = default;

void IDAWDialogHandler::DialogMenu::debug() {}

const Core::Vector<IDAWDialogHandler::DialogMenu *> &
IDAWDialogHandler::DialogMenu::sourcePortChildren() const {
  return children_;
}

} // namespace Presonus
