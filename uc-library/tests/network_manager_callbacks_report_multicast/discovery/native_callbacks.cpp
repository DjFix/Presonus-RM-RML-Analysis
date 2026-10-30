#include "fixture_manager.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/report.hpp"
#include "presonus/uc/server.hpp"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <vector>
using namespace Presonus::UC;
namespace {
std::vector<std::string> calls;
int reportMode = 0, reportIdentity = 0, reportCount = 0, formattingCount = 0;
std::string reportText, reportFormat;
std::string encode(const std::string &value) {
  std::string result;
  constexpr char digits[] = "0123456789abcdef";
  for (unsigned char c : value) {
    result += digits[c >> 4];
    result += digits[c & 15];
  }
  return result.empty() ? "-" : result;
}
void reportA(int severity, const char *text) {
  assert(severity == 0 && text[4095] == 0);
  calls.push_back("report");
  reportIdentity = 1;
  ++reportCount;
  reportText = text;
}
void reportB(int severity, const char *text) {
  reportA(severity, text);
  reportIdentity = 2;
}
void beforeFormat(char *text, std::size_t n, const char *format) {
  assert(n == 4095);
  ++formattingCount;
  reportFormat = format;
  calls.push_back("format");
  std::memset(text, 0xa5, 4096);
}
void afterFormat() {
  if (reportMode == 2)
    UCSetReportFunction(reportB);
}

std::string hex(const char *p) {
  std::ostringstream s;
  for (unsigned i = 0; i < 256; ++i)
    s << std::hex << std::setfill('0') << std::setw(2)
      << static_cast<unsigned>(static_cast<unsigned char>(p[i]));
  return s.str();
}
class UnknownServer final : public Server {
public:
  UnknownServer(presonus::uc::ServerState &s)
      : Server(presonus::uc::ServerSourcePortTag{}, s) {}
  int getType() const override { return 2; }
};
struct Listener final : INetworkListener {
  unsigned added = 0, changed = 0;
  void onServerAvailable(int id, const ServerInfo &info) override {
    if (id != 71 || std::strcmp(info.strings[0], "FixtureServer"))
      throw std::runtime_error("actual registrar added metadata");
    ++added;
  }
  void onServerUnavailable(int) override {
    throw std::runtime_error("unexpected removal");
  }
  void onServerChanged(int id) override {
    if (id != 71)
      throw std::runtime_error("actual registrar changed identity");
    ++changed;
  }
};
} // namespace
extern "C" Server *
__real__ZNK8Presonus2UC15ServerRegistrar4findEPvb(const ServerRegistrar *,
                                                  void *, bool);
extern "C" Server *
__wrap__ZNK8Presonus2UC15ServerRegistrar4findEPvb(const ServerRegistrar *s,
                                                  void *c, bool local) {
  calls.push_back(local ? "find-local" : "find-all");
  return __real__ZNK8Presonus2UC15ServerRegistrar4findEPvb(s, c, local);
}
extern "C" LocalServer *
__real__ZN8Presonus2UC11LocalServer4castEPNS0_6ServerE(Server *);
extern "C" LocalServer *
__wrap__ZN8Presonus2UC11LocalServer4castEPNS0_6ServerE(Server *s) {
  calls.push_back("local");
  return __real__ZN8Presonus2UC11LocalServer4castEPNS0_6ServerE(s);
}
extern "C" RemoteServer *
__real__ZN8Presonus2UC12RemoteServer4castEPNS0_6ServerE(Server *);
extern "C" RemoteServer *
__wrap__ZN8Presonus2UC12RemoteServer4castEPNS0_6ServerE(Server *s) {
  calls.push_back("remote");
  return __real__ZN8Presonus2UC12RemoteServer4castEPNS0_6ServerE(s);
}
extern "C" void
__real__ZN8Presonus2UC15ServerRegistrar16serverRegisteredEPNS0_11LocalServerE(
    ServerRegistrar *, LocalServer *);
extern "C" void
__wrap__ZN8Presonus2UC15ServerRegistrar16serverRegisteredEPNS0_11LocalServerE(
    ServerRegistrar *r, LocalServer *s) {
  calls.push_back("registered");
  __real__ZN8Presonus2UC15ServerRegistrar16serverRegisteredEPNS0_11LocalServerE(
      r, s);
}
extern "C" void
__real__ZN8Presonus2UC15ServerRegistrar19notifyServerChangedEPNS0_6ServerE(
    ServerRegistrar *, Server *);
extern "C" void
__wrap__ZN8Presonus2UC15ServerRegistrar19notifyServerChangedEPNS0_6ServerE(
    ServerRegistrar *r, Server *s) {
  calls.push_back("notify");
  __real__ZN8Presonus2UC15ServerRegistrar19notifyServerChangedEPNS0_6ServerE(r,
                                                                             s);
}
extern "C" int __real_vsnprintf(char *, std::size_t, const char *, va_list);
extern "C" int __wrap_vsnprintf(char *text, std::size_t n, const char *format,
                                va_list args) {
  beforeFormat(text, n, format);
  int result = __real_vsnprintf(text, n, format, args);
  afterFormat();
  return result;
}
extern "C" int __real___vsnprintf_chk(char *, std::size_t, int, std::size_t,
                                      const char *, va_list);
extern "C" int __wrap___vsnprintf_chk(char *text, std::size_t n, int flags,
                                      std::size_t capacity, const char *format,
                                      va_list args) {
  assert(capacity >= 4096);
  beforeFormat(text, n, format);
  int result = __real___vsnprintf_chk(text, n, flags, capacity, format, args);
  afterFormat();
  return result;
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ofstream out(argv[1]);
  presonus::uc::EventDispatcherState dispatcherState;
  EventDispatcher dispatcher(dispatcherState);
  presonus::uc::CclFactoryRegistry registry;
  EventFactory factory(registry.registry());
  const char *texts[] = {"null", "empty", "small", "254",
                         "255",  "256",   "511",   "self"};
  for (unsigned hookMode = 0; hookMode < 3; ++hookMode)
    for (unsigned mode = 0; mode < 2; ++mode)
      for (unsigned found = 0; found < 2; ++found)
        for (unsigned kind = 0; kind < 3; ++kind)
          for (unsigned fill : {0U, 90U, 255U})
            for (const char *textCase : texts) {
              presonus::uc::ServerState common;
              presonus::uc::RemoteServerState remoteState;
              common.strings[0] = "FixtureServer";
              common.localRegistrationByte = static_cast<unsigned char>(fill);
              remoteState.common.strings[0] = "FixtureServer";
              remoteState.common.localRegistrationByte =
                  static_cast<unsigned char>(fill);
              char *buffer = remoteState.addresses[1].getBuffer();
              std::memset(buffer, static_cast<int>(fill), 256);
              std::memcpy(buffer, "oldtail", 8);
              LocalServer local(presonus::uc::ServerSourcePortTag{}, common);
              RemoteServer remote(presonus::uc::ServerSourcePortTag{},
                                  remoteState);
              UnknownServer unknown(common);
              Server *server = kind == 0   ? static_cast<Server *>(&local)
                               : kind == 1 ? static_cast<Server *>(&remote)
                                           : static_cast<Server *>(&unknown);
              int context = 0;
              presonus::uc::AvailableServerView view;
              view.identity = server;
              view.localIdentity = kind == 0 ? &local : nullptr;
              view.registrationContext = &context;
              view.identifier = 71;
              view.strings[0] = "FixtureServer";
              presonus::uc::ServerRegistrarState registrarState;
              if (found) {
                registrarState.localServers.add(&view);
                registrarState.allServerViews.add(&view);
              }
              Listener listener;
              registrarState.listeners.add(&listener);
              ServerRegistrar registrar(registrarState);
              presonus::uc::NetworkManagerState state{dispatcher, factory};
              state.registrar = &registrar;
              FixtureManager manager(state);
              std::string text;
              const char *argument = nullptr;
              if (std::strcmp(textCase, "null")) {
                if (!std::strcmp(textCase, "small"))
                  text = "updated";
                else if (!std::strcmp(textCase, "self"))
                  argument = buffer;
                else if (std::strcmp(textCase, "empty"))
                  text.assign(std::stoul(textCase), 'x');
                if (!argument)
                  argument = text.c_str();
              }
              calls.clear();
              reportMode = static_cast<int>(hookMode);
              reportIdentity = reportCount = formattingCount = 0;
              reportText.clear();
              reportFormat.clear();
              UCSetReportFunction(hookMode == 0 ? nullptr : reportA);
              if (mode == 0)
                manager.onRegistrationCompleted(&context);
              else
                manager.onServerChanged(&context, argument);
              out << (mode == 0 ? "registered" : "changed") << '\t' << found
                  << '\t' << kind << '\t' << fill << '\t' << textCase << '\t'
                  << static_cast<unsigned>(
                         kind == 1 ? remoteState.common.localRegistrationByte
                                   : common.localRegistrationByte)
                  << '\t' << hex(buffer) << '\t';
              for (const auto &call : calls)
                out << call << ',';
              out << '\t' << listener.added << '\t' << listener.changed << '\t'
                  << hookMode << '\t' << reportIdentity << '\t' << reportCount
                  << '\t' << formattingCount << '\t' << encode(reportText)
                  << '\t' << encode(reportFormat) << '\n';
            }
}
