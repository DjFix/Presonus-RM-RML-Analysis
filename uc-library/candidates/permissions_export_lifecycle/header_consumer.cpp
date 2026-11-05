// This consumer deliberately includes no ClientSubscription definition.
#include "presonus/mixer/PermissionsComponent.hpp"
void permissionsHeaderConsumer(Presonus::Mixer::PermissionsBindings &bindings) {
  Presonus::Mixer::PermissionsComponent component(bindings);
}
