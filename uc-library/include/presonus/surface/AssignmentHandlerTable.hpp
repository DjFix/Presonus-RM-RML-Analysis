#pragma once
#include "core/public/corevector.h"
#include "presonus/surface/sl_mixer_encoder.hpp"
namespace Core::Portable {
class Component;
}
namespace Presonus {
class AssignmentHandler;
// Intentional source port. Composition, lifetime and ordinary returns are not
// original declarations or ARM layout claims. Non-owning handler pointers.
class AssignmentHandlerTable {
public:
  AssignmentHandlerTable();
  AssignmentHandlerTable(const AssignmentHandlerTable &other);
  explicit AssignmentHandlerTable(Core::Vector<AssignmentHandler *> &handlers)
      : handlers_(handlers) {}
  void initializeHandlers(Core::Portable::Component *);
  void addHandler(AssignmentHandler *);
  AssignmentHandler *getHandler(int) const;
  // Observed count and success values; original return declarations unresolved.
  int countHandlers() const;
  bool getParamFocusInfo(MixerAssignmentHandler::FocusInfo &,
                         Core::Portable::Parameter *);
  void removeHandler(AssignmentHandler *);
  // Provisional borrowed pointer return; original static declaration
  // unresolved.
  AssignmentHandler *findHandler(const char *) const;

private:
  Core::Vector<AssignmentHandler *> ownedHandlers_;
  Core::Vector<AssignmentHandler *> &handlers_;
};
} // namespace Presonus
