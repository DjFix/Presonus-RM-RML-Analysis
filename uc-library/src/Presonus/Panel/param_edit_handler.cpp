#include "presonus/panel/param_edit_handler.hpp"
#include "core/system/coretime.h"
#include "presonus/dice/packet_services.hpp"

namespace {
double nowSeconds() {
  // Explicit old-API compatibility binding: actual pinned source CCL converts
  // signed nanosecond ticks. This defines no old Core binary function body.
  return Core::SystemClock::toSeconds(presonus::dice::packetClockRawTicks());
}
} // namespace
namespace Presonus::Panel {
ParamEditHandler::ParamEditHandler() : edits_(64, 32), blockers_(32, 32) {}
ParamEditHandler::~ParamEditHandler() = default;

void ParamEditHandler::handleParamEdit(Core::Portable::Parameter *parameter) {
  if (!parameter)
    return;
  if (parameter->isEditing()) {
    for (int i = 0; i < edits_.count(); ++i) {
      if (edits_.at(i).parameter == parameter) {
        edits_.at(i).lastEdit = nowSeconds();
        return;
      }
    }
    return; // Already editing elsewhere: do not add or begin an unmanaged
            // entry.
  }
  const double time = nowSeconds();
  // Original calls resize(count+1) directly, not modern reserve's optional
  // exponential growth. Use actual CCL resize before add to retain that policy.
  if (edits_.count() < edits_.getCapacity() ||
      edits_.resize(edits_.count() + 1))
    edits_.add({parameter, time});
  // Original begins even if its vector growth failed and no entry was added.
  parameter->beginEdit();
}

void ParamEditHandler::addReceiveBlocker(Control *control) {
  for (int i = 0; i < blockers_.count(); ++i) {
    if (blockers_.at(i).control == control) {
      blockers_.at(i).lastReceive = nowSeconds();
      return;
    }
  }
  const double time = nowSeconds();
  if (blockers_.count() < blockers_.getCapacity() ||
      blockers_.resize(blockers_.count() + 1))
    blockers_.add({control, time});
}

bool ParamEditHandler::isReceiveBlocked(Control *control) const {
  for (int i = 0; i < blockers_.count(); ++i)
    if (blockers_.at(i).control == control)
      return true;
  return false;
}

void ParamEditHandler::onIdle() {
  if (edits_.count() <= 0 && blockers_.count() <= 0)
    return;
  const double time = nowSeconds();
  for (int i = edits_.count() - 1; i >= 0; --i) {
    if (time - edits_.at(i).lastEdit > 1.) {
      edits_.at(i).parameter->endEdit();
      // Framework callbacks may change count. Actual CCL removeAt performs the
      // fresh index/count check and sentinel clear observed in the original.
      edits_.removeAt(i);
    }
  }
  for (int i = blockers_.count() - 1; i >= 0; --i)
    if (time - blockers_.at(i).lastReceive > 1.)
      blockers_.removeAt(i);
}
} // namespace Presonus::Panel
