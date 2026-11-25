#include "presonus/surface/AssignmentHandlerTable.hpp"
#include <cstring>
namespace Presonus {
AssignmentHandlerTable::AssignmentHandlerTable() : handlers_(ownedHandlers_) {}

AssignmentHandlerTable::AssignmentHandlerTable(
    const AssignmentHandlerTable &other)
    : ownedHandlers_(other.ownedHandlers_),
      handlers_(&other.handlers_ == &other.ownedHandlers_ ? ownedHandlers_
                                                          : other.handlers_) {}

void AssignmentHandlerTable::initializeHandlers(
    Core::Portable::Component *component) {
  const int count = handlers_.count();
  AssignmentHandler *const *items = handlers_.getItems();
  for (int index = 0; index < count; ++index)
    items[index]->initialize(component);
}

AssignmentHandler *AssignmentHandlerTable::findHandler(const char *name) const {
  const int count = handlers_.count();
  AssignmentHandler *const *items = handlers_.getItems();
  const char *query = name ? name : "";
  for (int i = 0; i < count; ++i) {
    AssignmentHandler *handler = items[i];
    const char *candidate = handler->getName();
    if (std::strcmp(candidate ? candidate : "", query) == 0)
      return handler;
  }
  return nullptr;
}

AssignmentHandler *AssignmentHandlerTable::getHandler(int index) const {
  return handlers_.at(index);
}
int AssignmentHandlerTable::countHandlers() const { return handlers_.count(); }

bool AssignmentHandlerTable::getParamFocusInfo(
    MixerAssignmentHandler::FocusInfo &info,
    Core::Portable::Parameter *parameter) {
  const int count = handlers_.count();
  AssignmentHandler *const *items = handlers_.getItems();
  for (int index = 0; index < count; ++index) {
    auto *handler = items[index];
    if (!handler)
      continue;
    auto *mixer =
        static_cast<MixerAssignmentHandler *>(handler->castTo(0x4d784173));
    if (mixer && mixer->getParamFocusInfo(info, parameter))
      return true;
  }
  return false;
}

void AssignmentHandlerTable::removeHandler(AssignmentHandler *handler) {
  handlers_.remove(handler);
}
} // namespace Presonus
