#include "presonus/MappingTable.hpp"
#include <iostream>
struct Recorder final : presonus::mapping::ItemOperations {
  const char *call = "none";
  int flag = -1;
  Presonus::MappingTable::Item *seen = nullptr;
  void fullOff(Presonus::MappingTable::Item &i) override {
    call = "setFullOff";
    seen = &i;
  }
  void inverseMode(Presonus::MappingTable::Item &i, bool b) override {
    call = "setInverseMode";
    seen = &i;
    flag = b;
  }
  void enabled(Presonus::MappingTable::Item &i, bool b) override {
    call = "setEnabled";
    seen = &i;
    flag = b;
  }
  void immediate(Presonus::MappingTable::Item &i, bool b) override {
    call = "setImmediate";
    seen = &i;
    flag = b;
  }
};
int main() {
  // Genuine source-port object; legacy operations observe identity only.
  Core::Portable::ParamInfo aliasInfo{};
  aliasInfo.type = Core::Portable::ParamInfo::kAlias;
  Core::Portable::AliasParam alias(aliasInfo);
  Presonus::MappingTable::Item item(alias);
  for (int task = 1; task <= 5; ++task)
    for (int found = 0; found <= 1; ++found)
      for (int flag = 0; flag <= 1; ++flag) {
        Recorder recorder;
        const presonus::mapping::Entry entries[] = {
            {"aaa", &item}, {found ? "key" : "kkk", &item}, {"zzz", &item}};
        Presonus::MappingTable table(entries, 3, recorder);
        bool result = false;
        switch (task) {
        case 1:
          result = table.findItem("key") == &item;
          break;
        case 2:
          table.setControlFullOff("key");
          break;
        case 3:
          table.setControlInverseMode("key", flag);
          break;
        case 4:
          table.setControlEnabled("key", flag);
          break;
        case 5:
          table.setControlImmediate("key", flag);
          break;
        }
        std::cout << task << ' ' << found << ' ' << flag << ' ' << result << ' '
                  << recorder.call << ' ' << recorder.flag << ' '
                  << (recorder.seen == &item) << '\n';
      }
}
