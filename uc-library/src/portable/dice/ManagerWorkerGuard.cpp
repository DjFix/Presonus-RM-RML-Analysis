#include "ManagerWorkerGuard.hpp"
#include "core/system/corethread.h"
#include "presonus/dice/manager.hpp"
#include <algorithm>
#include <cstdlib>
#include <exception>
#include <stdexcept>
#include <vector>

namespace presonus::dice {
namespace {
struct ShutdownState {
  Core::Threads::Lock lock;
  std::vector<ManagerWorkerGuard *> workers;
  Core::Threads::ThreadID controller = 0;
  bool registered = false;
  bool closing = false;
};
// Process-lifetime reachable bookkeeping intentionally survives CCL registry
// teardown, so later Manager member destructors can safely unregister. It does
// not own Managers/threads and is not a replacement for Core's registry.
ShutdownState &state() {
  static auto *value = new ShutdownState;
  return *value;
}
void shutdownWorkers() noexcept {
  auto &s = state();
  {
    Core::Threads::ScopedLock guard(s.lock);
    if (s.controller != Core::Threads::CurrentThread::getID())
      std::terminate();
    s.closing = true;
  }
  for (;;) {
    ManagerWorkerGuard *worker = nullptr;
    {
      Core::Threads::ScopedLock guard(s.lock);
      if (s.workers.empty())
        break;
      worker = s.workers.back();
      s.workers.pop_back();
    }
    // Never join while holding registry, UART or receiver locks.
    worker->quiesce();
  }
}
} // namespace
ManagerWorkerGuard::ManagerWorkerGuard(Presonus::DICE::Dice3Manager &manager)
    : manager_(manager), controller_(Core::Threads::CurrentThread::getID()) {
  // Caller has already obtained UART::instance(), establishing CCL's actual
  // DeletableList before this atexit hook. This hook therefore runs first.
  auto &s = state();
  Core::Threads::ScopedLock guard(s.lock);
  if (s.controller == 0)
    s.controller = controller_;
  if (s.controller != controller_)
    throw std::logic_error("Manager lifecycle requires its controller thread");
  if (s.closing)
    throw std::logic_error("Manager construction during shutdown");
  if (!s.registered) {
    if (std::atexit(shutdownWorkers) != 0)
      throw std::runtime_error("Cannot register Manager worker shutdown");
    s.registered = true;
  }
  s.workers.push_back(this);
}
ManagerWorkerGuard::~ManagerWorkerGuard() {
  quiesce();
  auto &s = state();
  Core::Threads::ScopedLock guard(s.lock);
  auto it = std::find(s.workers.begin(), s.workers.end(), this);
  if (it != s.workers.end())
    s.workers.erase(it);
}
void ManagerWorkerGuard::quiesce() noexcept {
  if (controller_ != Core::Threads::CurrentThread::getID())
    std::terminate();
  manager_.setPortableStopByte(1);
  if (!requested_ || joined_) {
    manager_.retirePortableReceiver();
    return;
  }
  auto &thread = static_cast<Core::Threads::Thread &>(manager_);
  if (thread.getID() != 0) {
    // Self-destruction cannot safely join; fail explicitly instead of leaving
    // a detached worker accessing a destroyed Manager.
    if (thread.getID() == Core::Threads::CurrentThread::getID())
      std::terminate();
    // Actual CCL join ignores the pthread_join result. Tests capture the
    // real call/return and worker completion; this bool is not success proof.
    thread.join(0);
  }
  joined_ = true;
  manager_.retirePortableReceiver();
}
} // namespace presonus::dice
