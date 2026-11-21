#pragma once
#include "core/public/corevector.h"
namespace Core::Portable {
class Component;
}
namespace Presonus {
class AssignmentHandler;
// Intentional source port. Composition, lifetime and ordinary returns are not
// original declarations or ARM layout claims. Non-owning handler pointers.
class AssignmentHandlerTable {
public:
  explicit AssignmentHandlerTable(Core::Vector<AssignmentHandler *> &handlers)
      : handlers_(handlers) {}
  void initializeHandlers(Core::Portable::Component *);
  void addHandler(AssignmentHandler *);
  AssignmentHandler *getHandler(int) const;
  void removeHandler(AssignmentHandler *);
  // Provisional borrowed pointer return; original static declaration
  // unresolved.
  AssignmentHandler *findHandler(const char *) const;

private:
  Core::Vector<AssignmentHandler *> &handlers_;
};
} // namespace Presonus
