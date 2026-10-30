#include "presonus/dice/programmer_device_services.hpp"
#include "presonus/surface_panel/OutputPin.hpp"
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <fcntl.h>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <unistd.h>
class ProjectIO final : public presonus::surface_panel_port::OutputPinIO {
public:
  int stage = 0, throwStage = 0, openNumber = 0, failOpen = 0, opened = 0,
      closed = 0;
  std::map<FILE *, int> live;
  void checkpoint() {
    if (++stage == throwStage)
      throw std::runtime_error("injected IO callback exception");
  }
  FILE *open(const char *path, const char *) override {
    checkpoint();
    if (std::string(path).find("/sys/class/gpio/") != 0)
      throw std::runtime_error("unexpected path");
    if (++openNumber == failOpen)
      return nullptr;
    const char *dir = std::getenv("TMPDIR");
    if (!dir || std::string(dir).find(
                    "/home/rs/projects/opencs/ai-line-analysis/temp/") != 0)
      throw std::runtime_error("project TMPDIR");
    std::string name = std::string(dir) + "/pin-adapter-XXXXXX";
    int fd = mkstemp(name.data());
    if (fd < 0)
      throw std::runtime_error("project file");
    FILE *f = fdopen(fd, "w+b");
    live.emplace(f, fd);
    ++opened;
    return f;
  }
  int printPin(FILE *f, const char *fmt, int n) override {
    checkpoint();
    return fprintf(f, fmt, n);
  }
  int close(FILE *f) override {
    auto it = live.find(f);
    if (it == live.end())
      throw std::runtime_error("double/unknown fclose");
    int fd = it->second;
    live.erase(it);
    int result = fclose(f);
    if (result != 0)
      throw std::runtime_error("real fclose failed");
    errno = 0;
    if (fcntl(fd, F_GETFD) != -1 || errno != EBADF)
      throw std::runtime_error("descriptor still open");
    ++closed;
    return result;
  }
  void formatPath(char *p, std::size_t n, const char *fmt, int pin) override {
    checkpoint();
    snprintf(p, n, fmt, pin);
  }
  std::size_t write(const void *d, std::size_t s, std::size_t n,
                    FILE *f) override {
    checkpoint();
    return fwrite(d, s, n, f);
  }
  int buffering(FILE *f, char *b, int m, std::size_t n) override {
    checkpoint();
    return setvbuf(f, b, m, n);
  }
  int put(int c, FILE *f) override { return fputc(c, f); }
  int error() override { return errno; }
  void log(const char *) override {}
  void logSet(const char *, int, int) override {}
};
int main() {
  unsigned cases = 0;
  for (int pin : {-1, 29, 30})
    for (int failure = 0; failure != 4; ++failure) {
      ProjectIO io;
      io.failOpen = failure;
      {
        presonus::dice::LinuxProgrammerDeviceServices services(&io);
        auto owned = services.makeOutputPin(pin);
        if (pin >= 0 && failure == 0) {
          owned->set(0);
          owned->set(1);
        }
      }
      if (!io.live.empty() || io.opened != io.closed)
        throw std::runtime_error("normal/unset/open-failure leak");
      ++cases;
    }
  for (int stage = 1; stage <= 8; ++stage) {
    ProjectIO io;
    io.throwStage = stage;
    bool caught = false;
    try {
      presonus::dice::LinuxProgrammerDeviceServices services(&io);
      auto owned = services.makeOutputPin(29);
    } catch (const std::runtime_error &) {
      caught = true;
    }
    if (!caught || !io.live.empty() || io.opened != io.closed)
      throw std::runtime_error("constructor exception cleanup failed");
    ++cases;
  }
  std::cout
      << "{\"passed\":true,\"cases\":" << cases
      << ",\"real_fclose_once_per_open\":true,\"FD_EBADF_after_close\":true,"
         "\"constructor_exceptions_8_stages\":true,\"no_device_ops\":true}\n";
}
