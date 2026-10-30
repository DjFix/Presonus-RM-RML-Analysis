#include "presonus/application/ApplicationManagers.hpp"
#include "core/portable/corefile.h"
#include "core/system/coredebug.h"
#include <stdexcept>

DEFINE_SINGLETON(Presonus::OmapApplicationManager)
DEFINE_SINGLETON(Presonus::Mixer::MixerManager)

namespace presonus::startup {
const char *CclEnvironmentBindings::homeDirectory() {
  Core::Portable::FileUtils::getHomeDir(home_);
  return home_.str();
}
void CclEnvironmentBindings::starting(const char *name) {
  Core::DebugPrintf("Main: starting %s\n", name);
}
void CclEnvironmentBindings::unrecognized(const char *name) {
  Core::DebugPrintf(
      "***** Error! Couldn't start because mixer name not recognized: %s\n",
      name);
}
Bindings &ManagerEngine::bindings() {
  if (!bindings_)
    throw std::logic_error("application-manager dependencies are unresolved");
  return *bindings_;
}
void ManagerEngine::setCommandLine(int argc, char **argv) {
  state.argv = argv;
  state.argc = argc;
}
int ManagerEngine::idle() {
  return state.app ? bindings().idle(state.app) : -1;
}
int ManagerEngine::initTheApp() { return bindings().init(state.app); }
int ManagerEngine::shutdown() {
  if (!state.app)
    return 0;
  if (bindings().shutdown(state.app) != 0)
    return 0;
  if (state.app)
    bindings().release(state.app, role_);
  state.app = nullptr;
  return 1;
}
int ManagerEngine::restart() { return shutdown() ? startup(0) : 0; }
int ManagerEngine::runTests(int mode) {
  const int result =
      bindings().runTests(state.app, mode, state.argc, state.argv);
  if (result == 0) {
    if (state.app)
      bindings().release(state.app, role_);
    if (role_ == Role::Surface)
      state.app = nullptr;
  }
  return result;
}
int ManagerEngine::startup(int mode) {
  Core::CStringBuffer<256> path;
  path = bindings().homeDirectory();
  path.append("/device.txt");
  Core::CStringBuffer<64> name(role_ == Role::Surface ? "surface" : "storm");
  const Core::ConstString key("DEVICE_NAME");
  const Core::ConstString file(path.str());
  bindings().readDeviceName(name, key, file);
  bindings().starting(name.str());
  Kind kind;
  if (role_ == Role::Surface && name == "surface")
    kind = Kind::Surface;
  else if (role_ == Role::Mixer && name == "storm")
    kind = Kind::Storm;
  else if (role_ == Role::Mixer && name == "rogue")
    kind = Kind::Rogue;
  else if (role_ == Role::Mixer && name == "beast")
    kind = Kind::Beast;
  else if (role_ == Role::Mixer && name == "wolverine")
    kind = Kind::Wolverine;
  else if (role_ == Role::Mixer && name == "wolverine_l")
    kind = Kind::WolverineRML;
  else if (role_ == Role::Mixer && name == "gambit")
    kind = Kind::Gambit;
  else if (role_ == Role::Mixer && name == "gambit_l")
    kind = Kind::GambitRML;
  else {
    bindings().unrecognized(name.str());
    return 0;
  }
  state.app = bindings().construct(kind, mode);
  if (state.argc > 1)
    return runTests(mode);
  initTheApp();
  return bindings().run(state.app) > 0 ? 1 : 0;
}
} // namespace presonus::startup

namespace Presonus {
OmapApplicationManager::OmapApplicationManager()
    : engine(presonus::startup::Role::Surface) {}
OmapApplicationManager::~OmapApplicationManager() = default;
void OmapApplicationManager::setCommandLine(int argc, char **argv) {
  engine.setCommandLine(argc, argv);
}
int OmapApplicationManager::idle() { return engine.idle(); }
int OmapApplicationManager::initTheApp() { return engine.initTheApp(); }
int OmapApplicationManager::shutdown() { return engine.shutdown(); }
int OmapApplicationManager::restart() { return engine.restart(); }
int OmapApplicationManager::runTests(AppMode mode) {
  return engine.runTests(mode);
}
int OmapApplicationManager::startup(AppMode mode) {
  return engine.startup(mode);
}
namespace Mixer {
MixerManager::MixerManager() : engine(presonus::startup::Role::Mixer) {}
MixerManager::~MixerManager() = default;
void MixerManager::setCommandLine(int argc, char **argv) {
  engine.setCommandLine(argc, argv);
}
int MixerManager::idle() { return engine.idle(); }
int MixerManager::initTheApp() { return engine.initTheApp(); }
int MixerManager::shutdown() { return engine.shutdown(); }
int MixerManager::restart() { return engine.restart(); }
int MixerManager::runTests(int mode) { return engine.runTests(mode); }
int MixerManager::startup(int mode) { return engine.startup(mode); }
} // namespace Mixer
} // namespace Presonus
