#include "presonus/IDAWDialogHandler.hpp"
#include "core/portable/coreattributes.h"
#include <cstring>
#include <memory>

namespace Presonus {

IDAWDialogHandler::DialogMenu::DialogMenu() = default;
IDAWDialogHandler::DialogMenu::~DialogMenu() {
  for (int index = 0; index < children_.count(); ++index)
    delete children_.at(index);
}

bool IDAWDialogHandler::DialogMenu::hasChildren() const {
  return children_.count() > 0;
}

bool IDAWDialogHandler::DialogMenu::isSeparator() const {
  return title_ && std::strcmp(title_, "-") == 0;
}

void IDAWDialogHandler::DialogMenu::parse(
    const Core::Portable::Attributes &attributes) {
  const auto *items = attributes.getQueue("items");
  if (!items)
    return;

  const auto &values = items->getValues();
  for (int index = 0; index < values.count(); ++index) {
    const auto *item = values.at(index)->getAttributes();
    if (!item)
      continue;

    auto child = std::make_unique<DialogMenu>();
    child->depth_ = depth_ + 1;
    child->title_ = item->getString("title");
    child->name_ = item->getString("name");
    child->category_ = item->getString("category");

    DialogMenu *menu = child.get();
    if (children_.add(menu))
      child.release();

    if (const auto *subMenu = item->getAttributes("subMenu"))
      menu->parse(*subMenu);
  }
}

void IDAWDialogHandler::DialogMenu::debug() {}

const Core::Vector<IDAWDialogHandler::DialogMenu *> &
IDAWDialogHandler::DialogMenu::sourcePortChildren() const {
  return children_;
}

} // namespace Presonus
