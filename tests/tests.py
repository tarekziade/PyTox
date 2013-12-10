import re
import unittest

from tox import Tox
from time import sleep

SERVER = ["54.215.145.71", 33445, "6EDDEE2188EF579303C0766B4796DCBA89C93058B6032FEA51593DCD42FB746C"]

ADDR_SIZE = 76
CLIENT_ID_SIZE = 64

class TestTox(Tox):
    pass

class ToxTest(unittest.TestCase):
    def setUp(self):
        self.alice = TestTox()
        self.bob = TestTox()

        self.alice.bootstrap_from_address(SERVER[0], 1, SERVER[1], SERVER[2])
        self.bob.bootstrap_from_address(SERVER[0], 1, SERVER[1], SERVER[2])

        self.loop_until_connected()

    def tearDown(self):
        """
        t:kill
        """
        self.alice.kill()
        self.bob.kill()

    def loop(self, n):
        """
        t:do
        """
        for i in range(n):
            self.alice.do()
            self.bob.do()
            sleep(0.02)

    def loop_until_connected(self):
        """
        t:isconnected
        """
        while not self.alice.isconnected() or not self.bob.isconnected():
            self.loop(50)

    def wait_callback(self, obj, attr):
        count = 0
        THRESHOLD = 10

        while not getattr(obj, attr):
            self.loop(50)
            if count >= THRESHOLD:
                return False
            count += 1

        return True

    def bob_add_alice_as_friend(self):
        """
        t:add_friend
        t:add_friend_norequest
        t:on_friend_request
        t:get_friend_id
        """
        MSG = 'Hi, this is Bob.'
        bob_addr = self.bob.get_address()

        def on_friend_request(self, pk, message):
            assert pk == bob_addr[:CLIENT_ID_SIZE]
            assert message == MSG
            self.add_friend_norequest(pk)
            self.fr = True

        TestTox.on_friend_request = on_friend_request

        alice_addr = self.alice.get_address()
        self.alice.fr = False
        self.bob.add_friend(alice_addr, MSG)

        assert self.wait_callback(self.alice, 'fr')
        TestTox.on_friend_request = Tox.on_friend_request

        self.bid = self.alice.get_friend_id(bob_addr)
        self.aid = self.bob.get_friend_id(alice_addr)

    def test_boostrap(self):
        """
        t:bootstrap_from_address
        """
        assert self.alice.isconnected()
        assert self.bob.isconnected()

    def test_get_address(self):
        """
        t:get_address
        """
        assert len(self.alice.get_address()) == ADDR_SIZE
        assert len(self.bob.get_address()) == ADDR_SIZE

    def test_self_name(self):
        """
        t:set_name
        t:get_self_name
        """
        self.alice.set_name('Alice')
        self.loop(10)
        assert self.alice.get_self_name() == 'Alice'

    def test_self_status_message(self):
        """
        t:set_status_message
        t:get_self_status_message
        """
        MSG = 'Happy'
        self.alice.set_status_message(MSG)
        self.loop(10)
        assert self.alice.get_self_status_message() == MSG

    def test_tox(self):
        """
        t:size
        t:save
        t:load
        """
        assert self.alice.size() > 0
        data = self.alice.save()
        assert data != None
        addr = self.alice.get_address()

        self.alice.kill()
        self.alice = Tox()
        self.alice.load(data)
        assert addr == self.alice.get_address()

    def test_self_user_status(self):
        """
        t:set_user_status
        t:get_self_user_status
        """
        self.alice.set_user_status(Tox.USERSTATUS_BUSY)
        self.loop(10)
        assert self.alice.get_self_user_status() == Tox.USERSTATUS_BUSY

    def test_friend(self):
        """
        t:del_friend
        t:friend_exists
        t:get_client_id
        t:get_friendlist
        t:get_name
        t:on_action
        t:on_friend_message
        t:send_action
        t:send_message
        """

        #: Test friend request
        self.bob_add_alice_as_friend()

        assert self.alice.friend_exists(self.bid)
        assert self.bob.friend_exists(self.aid)

        #: Test friend exists
        assert not self.alice.friend_exists(self.bid + 1)
        assert not self.bob.friend_exists(self.aid + 1)

        #: Test get_cliend_id
        assert self.alice.get_client_id(self.bid) == \
                self.bob.get_address()[:CLIENT_ID_SIZE]
        assert self.bob.get_client_id(self.aid) == \
                self.alice.get_address()[:CLIENT_ID_SIZE]

        #: Test get_friendlist
        assert [self.bid] == self.alice.get_friendlist()
        assert [self.aid] == self.bob.get_friendlist()

        #: Test friend name
        NEWNAME = 'Jenny'
        AID = self.aid
        def on_name_change(self, fid, newname):
            assert fid == AID
            assert newname == NEWNAME
            self.nc = True

        TestTox.on_name_change = on_name_change

        self.bob.nc = False
        self.alice.set_name(NEWNAME)

        assert self.wait_callback(self.bob, 'nc')
        assert self.bob.get_name(self.aid) == NEWNAME
        TestTox.on_name_change = Tox.on_name_change

        #: Test message
        MSG = 'Hi, Bob!'
        BID = self.bid
        def on_friend_message(self, fid, message):
            assert fid == BID
            assert message == MSG
            self.fm = True

        TestTox.on_friend_message = on_friend_message

        self.bob.send_message(self.aid, MSG)
        self.alice.fm = False

        assert self.wait_callback(self.alice, 'fm')
        TestTox.on_friend_message = Tox.on_friend_message

        #: Test action
        ACTION = 'Kick'
        BID = self.bid
        def on_action(self, fid, action):
            assert fid == BID
            assert action == ACTION
            self.fa = True

        TestTox.on_action = on_action

        self.bob.send_action(self.aid, ACTION)
        self.alice.fa = False

        assert self.wait_callback(self.alice, 'fa')
        TestTox.on_action = Tox.on_action

        #: Test delete friend
        self.alice.del_friend(self.bid)
        self.loop(10)
        assert not self.alice.friend_exists(self.bid)

    def test_group(self):
        """
        t:add_groupchat
        t:group_message_send
        t:group_number_peers
        t:group_peername
        t:invite_friend
        t:join_groupchat
        t:on_group_invite
        t:on_group_message
        t:on_group_namelist_change
        """
        self.bob_add_alice_as_friend()

        #: Test group add
        group_id = self.bob.add_groupchat()
        assert group_id >= 0

        self.loop(50)

        BID = self.bid
        def on_group_invite(self, fid, pk):
            assert fid == BID
            assert len(pk) == CLIENT_ID_SIZE
            self.join_groupchat(fid, pk)
            self.gi = True

        TestTox.on_group_invite = on_group_invite

        def on_group_namelist_change(self, gid, peer_number, change):
            assert gid == group_id
            assert change == Tox.CHAT_CHANGE_PEER_ADD
            self.gn = True

        TestTox.on_group_namelist_change = on_group_namelist_change

        self.alice.gi = False
        self.alice.gn = False

        while True:
            try:
                self.bob.invite_friend(self.aid, group_id)
                break
            except:
                print '!'
                self.loop(10)

        assert self.wait_callback(self.alice, 'gi')
        if not self.alice.gn:
            assert self.wait_callback(self.alice, 'gn')

        TestTox.on_group_invite = Tox.on_group_invite
        TestTox.on_group_namelist_change = Tox.on_group_namelist_change

        #: Test group number of peers
        self.loop(50)
        assert self.bob.group_number_peers(group_id) == 2

        #: Test group peername
        self.alice.set_name('Alice')
        self.bob.set_name('Bob')

        def on_group_namelist_change(self, gid, peer_number, change):
            if change == Tox.CHAT_CHANGE_PEER_NAME:
                self.gn = True

        TestTox.on_group_namelist_change = on_group_namelist_change
        self.alice.gn = False

        assert self.wait_callback(self.alice, 'gn')
        TestTox.on_group_namelist_change = Tox.on_group_namelist_change

        peernames = [self.bob.group_peername(group_id, i) for i in
                     range(self.bob.group_number_peers(group_id))]

        assert 'Alice' in peernames
        assert 'Bob' in peernames

        #: Test group message
        AID = self.aid
        BID = self.bid
        MSG = 'Group message test'
        def on_group_message(self, gid, fgid, message):
            if fgid == AID:
                assert gid == group_id
                assert message == MSG
                self.gm = True

        TestTox.on_group_message = on_group_message
        self.alice.gm = False

        while True:
            try:
                self.bob.group_message_send(group_id, MSG)
                break
            except:
                self.loop(10)

        self.wait_callback(self.alice, 'gm')
        TestTox.on_group_message = Tox.on_group_message

if __name__ == '__main__':
    unittest.main()

    methods = set([x for x in dir(Tox)
                     if not x[0].isupper() and not x[0] == '_'])
    docs = "".join([getattr(ToxTest, x).__doc__ for x in dir(ToxTest)
            if getattr(ToxTest, x).__doc__ != None])

    tested = set(re.findall(r't:(.*?)\n', docs))
    not_tested = methods.difference(tested)

    print('Test Converage: %.2f%%' % (len(tested) * 100.0 / len(methods)))
    print('Not tested:\n    %s' % "\n    ".join(sorted(list(not_tested))))