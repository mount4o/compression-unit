import unittest
import os
import zlib
import random
import urllib.request

from myhdl import delay, now, Signal, intbv, ResetSignal, Simulation, \
                  Cosimulation, block, instance, StopSimulation, modbv, \
                  always, always_seq, always_comb, enum, Error

from deflate import IDLE, WRITE, READ, STARTC, STARTD, LBSIZE, IBSIZE, \
                    CWINDOW, COMPRESS, DECOMPRESS, OBSIZE, LMAX, LIBSIZE, \
                    DYNAMIC, LOBSIZE, LOWLUT, deflate

MAXW = CWINDOW
RET_BUFF = bytes()
WRITE_CHUNK_SIZE = 2500
SIM_INSTANCE = None

# max size of the buffer of data we'll be working with

def test_data(m, tlen=100, limit=False):
    print("MODE", m, tlen)
    if m == 0:
        str_data = " ".join(["Hello World! " + str(1) + " "
                             for i in range(tlen)])
        b_data = str_data.encode('utf-8')
    elif m == 1:
        str_data = " ".join(["   Hello World! " + str(i) + "     "
                             for i in range(tlen)])
        b_data = str_data.encode('utf-8')
    elif m == 2:
        str_data = " ".join(["Hi: " + str(random.randrange(0,0x1000)) + " "
                             for i in range(tlen)])
        b_data = str_data.encode('utf-8')
    elif m == 3:
        if DYNAMIC:
            b_data = bytes([random.randrange(0,0x100) for i in range(tlen)])
        else:
            # prevent method 0 (copy mode)
            str_data = " ".join(["   Hello World! " + str(i) + "     "
                             for i in range(tlen)])
            b_data = str_data.encode('utf-8')
    elif m == 4:
        str_data = "".join([str(random.randrange(0,2))
                             for i in range(tlen)])
        b_data = str_data.encode('utf-8')
    elif m == 5:
        str_data = ""
        b_data = str_data.encode('utf-8')
    elif m == 6:
        b_data = urllib.request.urlopen("http://v7f.eu").read()
    elif m == 7:
        b_data = urllib.request.urlopen("https://ajax.googleapis.com/ajax/libs/jquery/1.12.0/jquery.min.js").read()
        b_data = b_data[:MAX_BUFF_SIZE]
    else:
        raise Error("unknown test mode")
    if limit:
        b_data = b_data[:IBSIZE - 4 - 10]
    if not DYNAMIC:
        co = zlib.compressobj(strategy=zlib.Z_FIXED,wbits=LOBSIZE)
    else:
        co = zlib.compressobj(wbits=LOBSIZE)
    data1 = co.compress(b_data)
    data2 = co.flush()
    zl_data = data1 + data2
    print("zlib: From %d to %d bytes" % (len(b_data), len(zl_data)))
    # print(zl_data[:500])
    return b_data, zl_data

def data_io(b_data, i_mode, o_done,
                     i_data, o_iprogress, o_oprogress,
                     o_byte, i_waddr, i_raddr, clk, reset):
    global RET_BUFF
    print("=========== COMPRESS ===========")

    def tick():
        clk.next = not clk

    # if mode == 0:
    #     reset.next = 1
    #     tick()
    #     yield delay(5)
    #     reset.next = 0
    #     tick()
    #     yield delay(5)
    
    print("CLEAR OLD INPUT")

    i_mode.next = WRITE
    i_waddr.next = 0
    i_raddr.next = 0
    tick()
    yield delay(5)
    tick()
    yield delay(5)

    print("STARTC")
    i_mode.next = STARTC
    tick()
    yield delay(5)
    tick()
    yield delay(5)

    print(f"Write chunk size is {WRITE_CHUNK_SIZE}")
    print("WRITE")
    i = 0
    ri = 0
    slen = len(b_data) # 10000
    sresult = []
    wait = 0
    start = now()
    while True:
        if ri < o_oprogress:
            did_read = 1
            # print("do read", ri, o_oprogress)
            i_mode.next = READ
            i_raddr.next = ri
            tick()
            yield delay(5)
            tick()
            yield delay(5)
            if ri % WRITE_CHUNK_SIZE == 0:
                print(ri)
            ri = ri + 1
        else:
            did_read = 0

        if len(b_data) < 4 and i == 0:
            """
            Short length input, just write 4 bytes.
            This is an API limitation!
            """
            print("SHORT INPUT")
            i_mode.next = WRITE
            i_waddr.next = 4
            i_data.next = 0
            i = 1
        elif i < slen and len(b_data) > 0:
            if o_iprogress > i - MAXW:
                i_mode.next = WRITE
                i_waddr.next = i
                i_data.next = b_data[i % len(b_data)]
                # print("write", i, b_data[i % len(b_data)])
                i = i + 1
            else:
                # print("Wait for space", i)
                wait += 1
        else:
            i_mode.next = IDLE

        tick()
        yield delay(5)
        tick()
        yield delay(5)
    
        if did_read:
            # print("read", ri, o_oprogress, o_byte)
            sresult.append(bytes([o_byte]))

        if o_done:
            # print("DONE", o_oprogress, ri)
            if o_oprogress == ri:
                break;

    i_mode.next = IDLE

    print("IN/OUT/CYCLES/WAIT", slen, len(sresult),
          (now() - start) // 10, wait)
    sresult = b''.join(sresult)
    print("len sresult", len(sresult))
    rlen = min(len(b_data), slen)
    print("rlen", rlen)
    print(f"fpga deflate: {len(sresult)}")
    # print(sresult)
    # assert zlib.decompress(sresult)[:rlen], b_data[:rlen]
    # print("zlib test:", zlib.decompress(sresult)[:50])
    print("DONE!")
    RET_BUFF = sresult

def fpga_sim_deflate_compress(b_data):
    global RET_BUFF, WRITE_CHUNK_SIZE, SIM_INSTANCE
    WRITE_CHUNK_SIZE = len(b_data)
    i_mode = Signal(intbv(0)[3:])
    o_done = Signal(bool(0))

    i_data = Signal(intbv()[8:])
    o_byte = Signal(intbv()[8:])
    o_iprogress = Signal(intbv()[LMAX:])
    o_oprogress = Signal(intbv()[LMAX:])
    i_waddr = Signal(modbv()[LMAX:])
    i_raddr = Signal(modbv()[LMAX:])

    clk = Signal(bool(0))
    reset = ResetSignal(0, 1, True)

    dut = deflate(i_mode, o_done, i_data, o_iprogress, o_oprogress,
                      o_byte, i_waddr, i_raddr, clk, reset)

    data_loader = data_io(
        # mode,
        b_data,
        i_mode,
        o_done,
        i_data,
        o_iprogress,
        o_oprogress,
        o_byte,
        i_waddr,
        i_raddr,
        clk,
        reset,
    )

    if SIM_INSTANCE:
        SIM_INSTANCE.quit()
        SIM_INSTANCE = None

    SIM_INSTANCE = Simulation(dut, data_loader)
    SIM_INSTANCE.run(quiet=1)
    SIM_INSTANCE.quit()
    SIM_INSTANCE = None
    return RET_BUFF

# mode = 7
# b_data, zl_data = test_data(mode, 2500 if not LOWLUT else 1000)

# deflate_compress_sim(b_data, zl_data)
