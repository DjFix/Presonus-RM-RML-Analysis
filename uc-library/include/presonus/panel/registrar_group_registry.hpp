#pragma once
#include "core/public/corevector.h"
namespace Presonus::Panel {
class ControlGroup;
}
namespace presonus::panel_binding {
// Independent source-port registry: CCL owns the pointer-array storage, while
// every actual ControlGroup is borrowed. No original fields/layout/ownership
// or registration/lifecycle declaration is claimed.
struct RegistrarGroupRegistry {
  Core::Vector<Presonus::Panel::ControlGroup *> groups;
};
} // namespace presonus::panel_binding
