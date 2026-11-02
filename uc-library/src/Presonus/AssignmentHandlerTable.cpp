#include "presonus/surface/AssignmentHandlerTable.hpp"
namespace Presonus {
AssignmentHandler *AssignmentHandlerTable::getHandler(int index) const {
  return handlers_.at(index);
}
void AssignmentHandlerTable::removeHandler(AssignmentHandler *handler) {
  handlers_.remove(handler);
}
} // namespace Presonus
