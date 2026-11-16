#include "presonus/ThroughputTest.hpp"
#include <cstdio>
#include <cstring>
#include <new>
extern "C" void __real_core_free(void *);
extern "C" void __real__ZdlPv(void *);
extern "C" int __real_fclose(FILE *);
extern "C" void destroySelected(Presonus::ThroughputTest *) asm(
    "_ZN8Presonus14ThroughputTestD0Ev");
namespace {
void *buffer, *receiver;
FILE *files[3];
int fileCount, eventCount;
char events[32];
void record(char c) { events[eventCount++] = c; }
class Child : public Core::Portable::Component {
public:
  ~Child() override { record('C'); }
};
} // namespace
extern "C" void __wrap_core_free(void *p) {
  if (p && p == buffer)
    record('B');
  __real_core_free(p);
}
extern "C" int __wrap_fclose(FILE *p) {
  for (int i = 0; i < fileCount; ++i)
    if (p == files[i])
      record('F');
  return __real_fclose(p);
}
extern "C" void __wrap__ZdlPv(void *p) {
  if (p && p == receiver)
    record('D');
  __real__ZdlPv(p);
}
int main() {
  for (int n : {0, 1, 3}) {
    for (int mode : {0, 1, 2}) {
      unsigned char borrowed[16];
      std::memset(borrowed, 0x5a, sizeof borrowed);
      Core::IO::Buffer source;
      if (mode == 1) {
        Core::IO::Buffer owned(16u);
        source.take(owned);
      } else if (mode == 2) {
        Core::IO::Buffer alias(borrowed, 16, false);
        source.take(alias);
      }
      buffer = source.getAddress();
      auto *p = new Presonus::ThroughputTest(
          Presonus::ThroughputTest::SourcePortTag{}, n, source);
      if (!source.isNull())
        return 2;
      p->addChild(new Child);
      FILE *unrelated = std::tmpfile();
      if (!unrelated)
        return 3;
      fileCount = n;
      for (int i = 0; i < n; ++i) {
        files[i] = std::tmpfile();
        if (!files[i])
          return 4;
        p->adoptSourcePortFile(i, files[i]);
      }
      receiver = p;
      eventCount = 0;
      destroySelected(p);
      events[eventCount] = 0;
      char expected[32];
      int k = 0;
      if (mode == 1)
        expected[k++] = 'B';
      for (int i = 0; i < n; ++i)
        expected[k++] = 'F';
      expected[k++] = 'C';
      expected[k++] = 'D';
      expected[k] = 0;
      if (std::strcmp(events, expected))
        return 5;
      if (std::fputc('x', unrelated) == EOF || borrowed[0] != 0x5a)
        return 6;
      std::fclose(unrelated);
      std::printf("%s\n", events);
    }
  }
}
