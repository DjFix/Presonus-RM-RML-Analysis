#include "core/public/coreproperty.h"
#include "presonus/link/Messenger.hpp"
#include <cstdio>
#include <memory>

namespace {
class Handler final : public Core::IPropertyHandler {
public:
  Handler(unsigned &calls, unsigned &destructions)
      : calls_(calls), destructions_(destructions) {}
  ~Handler() { ++destructions_; }
  void setProperty(const Core::Property &) override { ++calls_; }
  void getProperty(Core::Property &) override { ++calls_; }
  void release() override { ++calls_; }

private:
  unsigned &calls_;
  unsigned &destructions_;
};
} // namespace

int main() {
  unsigned calls = 0;
  unsigned destructions = 0;
  {
    const auto first = std::make_unique<Handler>(calls, destructions);
    const auto second = std::make_unique<Handler>(calls, destructions);
    {
      Presonus::Link::Messenger receiver;
      if (receiver.boundMsgHandler() || receiver.releaseRequested())
        return 1;
      receiver.release();
      Core::IPropertyHandler *const sequence[] = {
          first.get(), second.get(), second.get(), nullptr, first.get()};
      for (const auto handler : sequence) {
        receiver.setMsgHandler(handler);
        const auto *observed = receiver.boundMsgHandler();
        if (observed != handler || !receiver.releaseRequested() || calls ||
            destructions)
          return 2;
        std::printf("handler %d\n", observed == first.get() ? 1
                                    : observed              ? 2
                                                            : 0);
      }
    }
    if (calls || destructions)
      return 3;
  }
  if (calls || destructions != 2)
    return 4;
}
