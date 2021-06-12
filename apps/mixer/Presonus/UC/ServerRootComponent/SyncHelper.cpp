void Presonus::UC::ServerRootComponent::SyncHelper::serializeEncoding(Core::IO::MemoryStream&, Presonus::UC::ServerComponent&, char const*, bool)
               (int32_t arg1, int32_t arg2, int32_t placeholder_2, char *placeholder_3, undefined4 placeholder_4,
               int32_t arg_4h)
{
    int32_t iVar1;
    int32_t iVar2;
    char *pcVar3;
    int32_t iVar4;
    int32_t iVar5;
    int32_t iVar6;
    int32_t iVar7;
    int32_t iVar8;
    undefined auStack5744 [4];
    undefined auStack5740 [44];
    int32_t var_1640h;
    int32_t var_1000h;
    undefined uStack1632;
    int32_t var_65ch;
    int32_t var_658h;
    int32_t var_654h;
    int32_t var_650h;
    int32_t var_64ch;
    int32_t var_648h;
    int32_t var_644h;
    int32_t var_640h;
    int32_t var_630h;
    int32_t *piStack1088;
    int32_t var_43ch;
    int32_t var_438h;
    int32_t *piStack568;
    int32_t var_234h;
    int32_t var_230h;
    int32_t var_22ch;
    code *pcStack48;
    int32_t var_2ch;
    undefined4 uStack4;
    
    // Presonus::UC::ServerRootComponent::SyncHelper::serializeEncoding(Core::IO::MemoryStream&,
    // Presonus::UC::ServerComponent&, char const*, bool)
    iVar1 = *(int32_t *)0xf83d4;
    uStack4 = 0xf7e04;
    iVar2 = *(int32_t *)(*(int32_t *)arg1 + 0x94);
    var_644h = ZEXT14(iVar2 == *(int32_t *)0xf83d0 || iVar2 == *(int32_t *)0xf83cc);

    if (iVar2 == *(int32_t *)0xf83d0 || iVar2 == *(int32_t *)0xf83cc) {

        Core::Text::Json::BinaryWriter::BinaryWriter(Core::IO::Stream*)((int32_t)auStack5744, arg2);

        (***(code ***)((int32_t)&pcStack48 + iVar1))(auStack5744, 0, 0);
        var_65ch = *(int32_t *)0xf83d8;
        var_64ch = 5;
        var_658h = 0;
        var_654h = 0;
        var_650h = 0;
        Core::Vector<Presonus::UC::ServerComponent::SyncContext::StringList>::resize(int)((int32_t)&var_65ch, 0);
        var_648h = (int32_t)&var_640h;
        piStack1088 = &var_438h;
        piStack568 = &var_230h;
        pcVar3 = *(char **)0xf83dc;
        if (placeholder_3 != (char *)0x0) {
            pcVar3 = placeholder_3;
        }
        var_644h = 0;
        var_43ch = 0;
        var_234h = 0;
        if (*pcVar3 == '\0') {
            (**(code **)(*(int32_t *)((int32_t)&pcStack48 + iVar1) + 0x1c))
                      (auStack5744, *(undefined4 *)0xf83e0, *(undefined4 *)0xf83e4);
        } else {
            (**(code **)(*(int32_t *)((int32_t)&pcStack48 + iVar1) + 0x1c))
                      (auStack5744, *(undefined4 *)0xf83e0, *(undefined4 *)0xf83f0, 0);
            (**(code **)(*(int32_t *)((int32_t)&pcStack48 + iVar1) + 0x1c))
                      (auStack5744, *(undefined4 *)0xf83f4, placeholder_3, 0);
        }
        Presonus::UC::ServerComponent::writeAll(Core::AttributeHandler&, Presonus::UC::ServerComponent::SyncContext&) const
                  (placeholder_2, (int32_t)auStack5744);
        if (var_654h != 0) {
            (***(code ***)((int32_t)&pcStack48 + *(int32_t *)0xf83d4))(auStack5744, *(undefined4 *)0xf83e8, 0);
            (**(code **)(*(int32_t *)((int32_t)&pcStack48 + *(int32_t *)0xf83d4) + 8))
                      (auStack5744, *(undefined4 *)0xf83ec, 0);
            iVar2 = var_658h;
            iVar1 = *(int32_t *)0xf83d4;
            if (var_654h != 0) {
                iVar8 = 0;
                iVar7 = var_654h;
                do {
                    iVar6 = *(int32_t *)(iVar2 + iVar8 + 4);
                    iVar5 = *(int32_t *)(iVar2 + iVar8);
                    (**(code **)(*(int32_t *)((int32_t)&pcStack48 + iVar1) + 8))(auStack5744, 0, 0);
                    if (0 < iVar6) {
                        iVar4 = 0;
                        do {
                            (**(code **)(*(int32_t *)((int32_t)&pcStack48 + iVar1) + 0x1c))
                                      (auStack5744, 0, *(undefined4 *)(iVar5 + iVar4 * 4), 0);
                            iVar4 = iVar4 + 1;
                        } while (iVar4 < iVar6);
                    }
                    (**(code **)(*(int32_t *)((int32_t)&pcStack48 + iVar1) + 0xc))(auStack5744, 0, 0);
                    iVar7 = iVar7 + -1;
                    iVar8 = iVar8 + 8;
                } while (iVar7 != 0);
            }
            (**(code **)(*(int32_t *)((int32_t)&pcStack48 + *(int32_t *)0xf83d4) + 0xc))
                      (auStack5744, *(undefined4 *)0xf83ec, 0);
            (**(code **)(*(int32_t *)((int32_t)&pcStack48 + *(int32_t *)0xf83d4) + 4))
                      (auStack5744, *(undefined4 *)0xf83e8, 0);
        }
        (**(code **)(*(int32_t *)((int32_t)&pcStack48 + *(int32_t *)0xf83d4) + 4))(auStack5744, 0, 0);
        Core::Vector<Presonus::UC::ServerComponent::SyncContext::StringList>::~Vector()((int32_t)&var_65ch);
    } else {

        Core::Text::Json::Writer::Writer(Core::IO::Stream*)((int32_t)auStack5744);

        uStack1632 = (undefined)placeholder_4;
        (***(code ***)((int32_t)&pcStack48 + iVar1))(auStack5744, var_644h, var_644h);
        var_65ch = *(int32_t *)0xf83d8;
        var_64ch = 5;
        var_658h = var_644h;
        var_654h = var_644h;
        var_650h = var_644h;
        Core::Vector<Presonus::UC::ServerComponent::SyncContext::StringList>::resize(int)((int32_t)&var_65ch, var_644h);
        piStack1088 = &var_438h;
        var_648h = (int32_t)&var_640h;
        piStack568 = &var_230h;
        pcVar3 = *(char **)0xf83dc;
        if (placeholder_3 != (char *)0x0) {
            pcVar3 = placeholder_3;
        }
        var_43ch = var_644h;
        var_234h = var_644h;
        if (*pcVar3 == '\0') {
            (**(code **)(*(int32_t *)((int32_t)&pcStack48 + iVar1) + 0x1c))
                      (auStack5744, *(undefined4 *)0xf83e0, *(undefined4 *)0xf83e4);
        } else {
            (**(code **)(*(int32_t *)((int32_t)&pcStack48 + iVar1) + 0x1c))
                      (auStack5744, *(undefined4 *)0xf83e0, *(undefined4 *)0xf83f0, var_644h);
            (**(code **)(*(int32_t *)((int32_t)&pcStack48 + iVar1) + 0x1c))
                      (auStack5744, *(undefined4 *)0xf83f4, placeholder_3, iVar1 + 0x1640);
        }
        Presonus::UC::ServerComponent::writeAll(Core::AttributeHandler&, Presonus::UC::ServerComponent::SyncContext&) const
                  (placeholder_2, (int32_t)auStack5744);
        if (var_654h != 0) {
            (***(code ***)((int32_t)&pcStack48 + *(int32_t *)0xf83d4))(auStack5744, *(undefined4 *)0xf83e8, 0);
            (**(code **)(*(int32_t *)((int32_t)&pcStack48 + *(int32_t *)0xf83d4) + 8))
                      (auStack5744, *(undefined4 *)0xf83ec, 0);
            iVar2 = var_658h;
            iVar1 = *(int32_t *)0xf83d4;
            if (var_654h != 0) {
                iVar8 = 0;
                iVar7 = var_654h;
                do {
                    iVar6 = *(int32_t *)(iVar2 + iVar8 + 4);
                    iVar5 = *(int32_t *)(iVar2 + iVar8);
                    (**(code **)(*(int32_t *)((int32_t)&pcStack48 + iVar1) + 8))(auStack5744, 0, 0);
                    if (0 < iVar6) {
                        iVar4 = 0;
                        do {
                            (**(code **)(*(int32_t *)((int32_t)&pcStack48 + iVar1) + 0x1c))
                                      (auStack5744, 0, *(undefined4 *)(iVar5 + iVar4 * 4), 0);
                            iVar4 = iVar4 + 1;
                        } while (iVar4 < iVar6);
                    }
                    (**(code **)(*(int32_t *)((int32_t)&pcStack48 + iVar1) + 0xc))(auStack5744, 0, 0);
                    iVar7 = iVar7 + -1;
                    iVar8 = iVar8 + 8;
                } while (iVar7 != 0);
            }
            (**(code **)(*(int32_t *)((int32_t)&pcStack48 + *(int32_t *)0xf83d4) + 0xc))
                      (auStack5744, *(undefined4 *)0xf83ec, 0);
            (**(code **)(*(int32_t *)((int32_t)&pcStack48 + *(int32_t *)0xf83d4) + 4))
                      (auStack5744, *(undefined4 *)0xf83e8, 0);
        }
        (**(code **)(*(int32_t *)((int32_t)&pcStack48 + *(int32_t *)0xf83d4) + 4))(auStack5744, 0, 0);
        Core::Vector<Presonus::UC::ServerComponent::SyncContext::StringList>::~Vector()((int32_t)&var_65ch);
        Core::Text::TextWriter::flush()((int32_t)auStack5740);
    }
    return;
}

void Presonus::UC::ServerRootComponent::SyncHelper::sendPartToAll(Presonus::UC::ServerComponent&)
               (int32_t arg1, int32_t arg2)
{
    int32_t in_stack_fffffe8c;
    undefined auStack364 [4];
    int32_t var_168h;
    undefined auStack108 [4];
    int32_t var_68h;
    undefined auStack84 [4];
    int32_t var_50h;
    int32_t iStack68;
    int32_t var_40h;
    int32_t var_3ch;
    int32_t var_38h;
    undefined4 uStack4;
    
    // Presonus::UC::ServerRootComponent::SyncHelper::sendPartToAll(Presonus::UC::ServerComponent&)
    uStack4 = 0xf8404;
    Core::CStringBuffer<256>::CStringBuffer(char const*)((int32_t)auStack364, 0);
    Core::Portable::Component::getComponentPath(Core::CStringBuffer<256>&) const(arg2, (int32_t)auStack364);
    method.Core::IO::MemoryStream.MemoryStream_unsigned_int((int32_t)&iStack68, 0x2000);
    Presonus::UC::ServerRootComponent::SyncHelper::serializeEncoding(Core::IO::MemoryStream&, Presonus::UC::ServerComponent&, char const*, bool)
              (arg1, (int32_t)&iStack68, arg2, auStack364, 1, in_stack_fffffe8c);
    method.Presonus::UC::MutableMessageEvent.MutableMessageEvent((int32_t)auStack108);
    Presonus::UC::MutableMessageEvent::assign(Core::IO::MemoryStream&, int)((int32_t)auStack108);
    Presonus::UC::ServerImplementation::sendToClients(Presonus::UC::Event&, int)
              (*(int32_t *)arg1 + 0x88, (int32_t)auStack108);
    method.Core::IO::Buffer._Buffer((uint32_t)auStack84);
    var_40h = *(int32_t *)0xf84dc + 0x28;
    iStack68 = *(int32_t *)0xf84dc;
    method.Core::IO::Buffer._Buffer((uint32_t)&var_3ch);
    return;
}

