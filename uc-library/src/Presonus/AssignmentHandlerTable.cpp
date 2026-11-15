#include "presonus/surface/AssignmentHandlerTable.hpp"
#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstring>
namespace Presonus {
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
void AssignmentHandlerTable::removeHandler(AssignmentHandler *handler) {
  handlers_.remove(handler);
}
} // namespace Presonus
