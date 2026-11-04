#pragma once
#include "core/public/corevector.h"
namespace Presonus {
class AssignmentHandler;
// Intentional source port. Composition, lifetime and ordinary returns are not
// original declarations or ARM layout claims. Non-owning handler pointers.
class AssignmentHandlerTable {
public:
  explicit AssignmentHandlerTable(Core::Vector<AssignmentHandler *> &handlers)
      : handlers_(handlers) {}
  void addHandler(AssignmentHandler *);
  AssignmentHandler *getHandler(int) const;
  void removeHandler(AssignmentHandler *);

private:
  Core::Vector<AssignmentHandler *> &handlers_;
};
} // namespace Presonus
