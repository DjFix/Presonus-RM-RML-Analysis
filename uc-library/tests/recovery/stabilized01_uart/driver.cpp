#include "presonus/panel/FrontPanelComponent.hpp"
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <sys/types.h>
#include <termios.h>
#include <time.h>
#include <vector>
namespace {
bool running = false;
std::string scenario;
std::deque<int> queues[2];
std::vector<std::string> opens, messages;
std::vector<std::pair<int, std::string>> writes;
std::vector<std::pair<int, int>> reads;
std::vector<int> closes;
long ticks = 0;
int port(int fd) {
  if (fd == 101)
    return 0;
  if (fd == 102)
    return 1;
  std::abort();
}
std::string json(const std::string &s) {
  std::ostringstream o;
  o << '"';
  for (unsigned char c : s) {
    if (c == '"' || c == '\\')
      o << '\\' << char(c);
    else if (c == '\n')
      o << "\\n";
    else if (c == '\r')
      o << "\\r";
    else if (c == '\t')
      o << "\\t";
    else if (c < 32) {
      o << "\\u00" << std::hex << std::setw(2) << std::setfill('0')
        << unsigned(c) << std::dec;
    } else
      o << char(c);
  }
  return o.str() + '"';
}
struct Reject final : presonus::frontpanel_port::Dependencies {
  void perform(presonus::frontpanel_port::Action, int, int) override {
    std::abort();
  }
  bool timerLongEnough() const override { std::abort(); }
  bool fadersLocked() const override { std::abort(); }
  const char *activePageName() const override { std::abort(); }
  void paste(void *, const void *, const char *) override { std::abort(); }
};
} // namespace
extern "C" {
int __wrap_open(const char *path, int, ...) {
  if (!running)
    std::abort();
  opens.push_back(path);
  if (std::strcmp(path, "/dev/ttyS0") == 0)
    return 101;
  if (std::strcmp(path, "/dev/ttyS1") == 0)
    return 102;
  std::abort();
}
int __wrap_close(int fd) {
  if (!running)
    std::abort();
  closes.push_back(port(fd));
  return 0;
}
ssize_t __wrap_write(int fd, const void *p, size_t n) {
  if (!running)
    std::abort();
  writes.emplace_back(port(fd), std::string(static_cast<const char *>(p), n));
  return scenario == "short-write" ? 0 : static_cast<ssize_t>(n);
}
ssize_t __wrap_read(int fd, void *p, size_t n) {
  if (!running || n != 1)
    std::abort();
  int k = port(fd);
  if (queues[k].empty())
    std::abort();
  int v = queues[k].front();
  queues[k].pop_front();
  reads.emplace_back(k, v);
  if (v == 0)
    return -1;
  *static_cast<unsigned char *>(p) = v;
  return 1;
}
int __wrap_ioctl(int fd, unsigned long, ...) {
  port(fd);
  if (!running)
    std::abort();
  return 0;
}
int __wrap_tcgetattr(int fd, termios *t) {
  port(fd);
  if (!running)
    std::abort();
  std::memset(t, 0, sizeof(*t));
  return 0;
}
int __wrap_tcsetattr(int fd, int, const termios *) {
  port(fd);
  if (!running)
    std::abort();
  return 0;
}
int __wrap_cfsetspeed(termios *, speed_t) {
  if (!running)
    std::abort();
  return 0;
}
void __wrap_cfmakeraw(termios *) {
  if (!running)
    std::abort();
}
int __wrap_fcntl(int fd, int, ...) {
  port(fd);
  if (!running)
    std::abort();
  return 0;
}
int __real_clock_gettime(clockid_t, timespec *);
int __wrap_clock_gettime(clockid_t clock, timespec *t) {
  if (!running)
    return __real_clock_gettime(clock, t);
  ticks += 1000000;
  t->tv_sec = ticks / 1000000000;
  t->tv_nsec = ticks % 1000000000;
  return 0;
}
int __wrap___printf_chk(int, const char *fmt, ...) {
  char b[4096];
  va_list v;
  va_start(v, fmt);
  int n = vsnprintf(b, sizeof(b), fmt, v);
  va_end(v);
  if (running) {
    std::string s = b;
    if (s.rfind("UART:", 0) != 0 && s.rfind("write failed:", 0) != 0)
      messages.push_back(s);
  }
  return n;
}
int __wrap_printf(const char *fmt, ...) {
  char b[4096];
  va_list v;
  va_start(v, fmt);
  int n = vsnprintf(b, sizeof(b), fmt, v);
  va_end(v);
  if (running) {
    std::string s = b;
    if (s.rfind("UART:", 0) != 0 && s.rfind("write failed:", 0) != 0)
      messages.push_back(s);
  }
  return n;
}
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  scenario = argv[1];
  std::string probe = "PreSonus StudioLive AI";
  for (int k = 0; k < 2; ++k)
    for (unsigned char c : probe)
      queues[k].push_back(c);
  if (scenario == "first-mismatch")
    queues[0][1] = 'X';
  if (scenario == "second-mismatch")
    queues[1][1] = 'X';
  if (scenario == "timeout-after-sync")
    queues[0][3] = 0;
  if (scenario == "sync-junk-timeout") {
    queues[0].push_front(0);
    queues[0].push_front('x');
    queues[0].push_front(0);
    queues[1].push_front(0);
    queues[1].push_front('z');
  }
  Core::Portable::Component settings("settings");
  presonus::frontpanel_port::State state(settings);
  Reject dependencies;
  Presonus::Panel::FrontPanelComponent panel(state, dependencies);
  running = true;
  panel.uartTest();
  running = false;
  std::cout << "{\"opens\":[";
  for (size_t i = 0; i < opens.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << json(opens[i]);
  }
  std::cout << "],\"writes\":[";
  for (size_t i = 0; i < writes.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << '[' << writes[i].first << ',' << json(writes[i].second) << ']';
  }
  std::cout << "],\"reads\":[";
  for (size_t i = 0; i < reads.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << '[' << reads[i].first << ',' << reads[i].second << ']';
  }
  std::cout << "],\"closes\":[";
  for (size_t i = 0; i < closes.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << closes[i];
  }
  std::cout << "],\"messages\":[";
  for (size_t i = 0; i < messages.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << json(messages[i]);
  }
  std::cout << "]}\n";
}
