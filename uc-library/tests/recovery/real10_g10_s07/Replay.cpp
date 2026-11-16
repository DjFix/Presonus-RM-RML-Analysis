#include "presonus/ThroughputTest.hpp"
#include <cerrno>
#include <cstdio>
#include <fcntl.h>
#include <unistd.h>
extern "C" int __real_fclose(FILE *);
namespace {
FILE *watched;
int closes;
} // namespace
extern "C" int __wrap_fclose(FILE *f) {
  if (f == watched)
    ++closes;
  return __real_fclose(f);
}
int main() {
  for (bool present : {false, true}) {
    FILE *owned = present ? std::tmpfile() : nullptr;
    FILE *borrowed = std::tmpfile();
    if ((present && !owned) || !borrowed)
      return 2;
    int fd = present ? fileno(owned) : -1;
    watched = owned;
    closes = 0;
    {
      Presonus::ThroughputTest::WriteRecord r(
          Presonus::ThroughputTest::WriteRecord::SourcePortTag{}, owned);
    }
    if (closes != int(present))
      return 3;
    if (present && (fcntl(fd, F_GETFD) != -1 || errno != EBADF))
      return 4;
    if (std::fputc('x', borrowed) == EOF || std::fflush(borrowed))
      return 5;
    std::fclose(borrowed);
    std::printf("1 %d 1\n", closes);
  }
}
