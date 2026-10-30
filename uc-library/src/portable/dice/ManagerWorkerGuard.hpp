#pragma once
#include "core/system/corethread.h"
namespace Presonus::DICE {
class Dice3Manager;
}
namespace presonus::dice {
// Independent source-port guard. Lifecycle construction/destruction occurs on
// the controller thread; the owned worker never manages this registration.
class ManagerWorkerGuard {
public:
  explicit ManagerWorkerGuard(Presonus::DICE::Dice3Manager &);
  ~ManagerWorkerGuard();
  void requestStart() { requested_ = true; }
  void quiesce() noexcept;
  ManagerWorkerGuard(const ManagerWorkerGuard &) = delete;
  ManagerWorkerGuard &operator=(const ManagerWorkerGuard &) = delete;

private:
  Presonus::DICE::Dice3Manager &manager_;
  Core::Threads::ThreadID controller_;
  bool requested_ = false;
  bool joined_ = false;
};
} // namespace presonus::dice
