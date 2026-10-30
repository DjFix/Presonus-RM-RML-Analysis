#pragma once
#include "core/portable/corefilename.h"
#include "core/portable/coresingleton.h"
#include "core/public/corestringbuffer.h"
#include <cstdint>

namespace presonus::startup {
enum class Kind {
  Surface,
  Storm,
  Rogue,
  Beast,
  Wolverine,
  WolverineRML,
  Gambit,
  GambitRML
};
enum class Role { Surface, Mixer };
struct State {
  int argc = 0;
  char **argv = nullptr;
  void *app = nullptr;
};
// Named unresolved application endpoints. Implementations must supply real
// application behavior; the library provides no successful dummy application.
class Bindings {
public:
  virtual ~Bindings() = default;
  virtual const char *homeDirectory() = 0;
  virtual void readDeviceName(Core::CStringBuffer<64> &,
                              const Core::ConstString &key,
                              const Core::ConstString &path) = 0;
  virtual void starting(const char *) = 0;
  virtual void unrecognized(const char *) = 0;
  virtual void *construct(Kind, int mode) = 0;
  virtual int init(void *) = 0;
  virtual int run(void *) = 0;
  virtual int idle(void *) = 0;
  virtual int shutdown(void *) = 0;
  virtual int runTests(void *, int mode, int argc, char **argv) = 0;
  // Surface: original base-vptr write + direct delete. Mixer: virtual D0.
  virtual void release(void *, Role) = 0;
};
// Actual modern CCL environment adapter. Reader/application endpoints stay
// abstract until their implementations are recovered; no fake application.
class CclEnvironmentBindings : public Bindings {
public:
  const char *homeDirectory() override;
  void starting(const char *) override;
  void unrecognized(const char *) override;

private:
  Core::Portable::FileName home_;
};
class ManagerEngine {
public:
  explicit ManagerEngine(Role role) : role_(role) {}
  State state;
  void bind(Bindings &bindings) { bindings_ = &bindings; }
  void setCommandLine(int argc, char **argv);
  int idle();
  int initTheApp();
  int shutdown();
  int restart();
  int runTests(int mode);
  int startup(int mode);

private:
  Bindings &bindings();
  Role role_;
  Bindings *bindings_ = nullptr;
};
} // namespace presonus::startup

namespace Presonus {
// Original enumerator list/underlying declaration is unavailable. Source-port
// int backing retains the typed encoded interface, without ARM layout claim.
enum AppMode : int {};
class OmapApplicationManager
    : public Core::Portable::Singleton<OmapApplicationManager> {
public:
  OmapApplicationManager();
  ~OmapApplicationManager() override;
  void setCommandLine(int, char **);
  int idle();
  int initTheApp();
  int shutdown();
  int restart();
  int runTests(AppMode);
  int startup(AppMode);
  presonus::startup::ManagerEngine engine;
};
namespace Mixer {
class MixerManager : public Core::Portable::Singleton<MixerManager> {
public:
  MixerManager();
  ~MixerManager() override;
  void setCommandLine(int, char **);
  int idle();
  int initTheApp();
  int shutdown();
  int restart();
  int runTests(int);
  int startup(int);
  presonus::startup::ManagerEngine engine;
};
} // namespace Mixer
} // namespace Presonus
