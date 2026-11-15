#include "presonus/surface_update/FirmwareUpdateComponent.hpp"
#include <cstddef>
#include <cstring>
#include <iostream>
#include <string>
namespace presonus::surface_update {
struct ConstructionAccess {
  static bool worker(const Presonus::Surface::FirmwareUpdateComponent &v) {
    return bool(v.worker);
  }
  static bool
  progressNull(const Presonus::Surface::FirmwareUpdateComponent &v) {
    return v.progressParameter == nullptr;
  }
  static std::uint32_t
  word(const Presonus::Surface::FirmwareUpdateComponent &v) {
    return v.observedTaskWord;
  }
};
} // namespace presonus::surface_update
namespace {
class WorkerObservation : public Core::Portable::BackgroundWorker {
public:
  bool idle() const {
    return currentTask == nullptr && thread == nullptr && !shouldTerminate &&
           tasks.isEmpty();
  }
};
bool tracking = false;
void *workerAllocation = nullptr;
bool workerAllocated = false, workerFreed = false;
} // namespace
extern "C" void *__real__Znwm(std::size_t);
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void *__wrap__Znwm(std::size_t bytes) {
  void *p = __real__Znwm(bytes);
  if (tracking && bytes == sizeof(Core::Portable::BackgroundWorker)) {
    workerAllocation = p;
    workerAllocated = true;
  }
  return p;
}
extern "C" void __wrap__ZdlPv(void *p) {
  if (tracking && p == workerAllocation)
    workerFreed = true;
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (tracking && p == workerAllocation)
    workerFreed = true;
  __real__ZdlPvm(p, n);
}
int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "--observe-provider") {
    Core::Portable::Component component("firmwareupdate");
    WorkerObservation worker;
    std::cout << "{\"component_name\":\"" << component.getName()
              << "\",\"worker_idle\":" << (worker.idle() ? "true" : "false")
              << ",\"host_worker_size\":"
              << sizeof(Core::Portable::BackgroundWorker) << "}\n";
    return 0;
  }
  using A = presonus::surface_update::ConstructionAccess;
  tracking = true;
  {
    Presonus::Surface::FirmwareUpdateComponent component;
    std::cout << component.getName() << ' ' << A::worker(component) << ' '
              << A::progressNull(component) << ' ' << A::word(component) << ' ';
  }
  tracking = false;
  std::cout << workerAllocated << ' ' << workerFreed << '\n';
  {
    Presonus::Surface::FirmwareUpdateComponent callbacks(
        presonus::surface_update::CallbackSourcePort{}, nullptr, 0, nullptr);
    std::cout << callbacks.getName() << ' ' << A::worker(callbacks) << ' '
              << A::progressNull(callbacks) << '\n';
  }
}
