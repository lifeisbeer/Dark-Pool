// SPDX-License-Identifier: UNLICENSED

pragma solidity ^0.8.1;
pragma abicoder v2;
pragma experimental SMTChecker;

// might need to change bytes to bytes32, have to check sizes of keys, hashes etc
contract darkPool {
    // State:
    //      Registration (Reg): operator can add, delete and modify client data,
    //      Trading (Tr): clients commit orders
    //      Reveil (Rev): clients "reveil" orders
    //      Calculation (Cal): operator performs the computation
    //      Results (Res): operator publishes matched orders
    // Then we move back to registration (next "trading day")
    enum Phase { Reg, Trd, Rev, Cal, Res }
    Phase public phase;
    enum Mode { APeriodic, APlato, AVolume, AOrdered,
                BPeriodic, BPlato, BVolume, BOrdered }
    Mode public mode;
    address public operator; // adress of the dark pool operator
    bytes[] p_keys;
    uint registered;
    uint used;
    mapping(address => bytes) public us_pk; // user specific public key
    // Stores details about each order
    struct Order {
        bytes _commitment;
        bytes _signiture;
        bytes _ciphertext;
        bytes _sk;
    }
    // Stores user orders
    mapping(address => Order) public orders;
    uint public expiration;

    // inform participants about current state
    event startPhase(
        Phase currentState,
        uint expirationTime
    );

    // inform participants about "revealed" commitments only since
    // the rest are automatically rejected (invalid)
    event commitmentRevealed(
        address sender,
        bytes commitment,
        bytes ciphertext
    );

    // reveal secret for a matched order
    event secretRevealed(
      address sender,
      bytes commitment,
      bytes ciphertext,
      bytes secret
    );

    // log trades after they were matched
    event logTrade(
        string buyer,
        string seller,
        uint amount,
        uint price
    );

    constructor(Mode m) {
        // save address of dark pool operator
        operator = msg.sender;
        // save Mode
        mode = m;
        // start registration phase
        phase = Phase.Reg;
        // set variables
        registered = 0;
        used = 0;
        // emit event
        emit startPhase(Phase.Reg, 0);
    }

    // *** Operator functions ***

    function add_key(bytes memory pk) external {
        // only the operator can add new clients
        require(msg.sender == operator, "Only the operator can call this.");
        // check if we are at the registration phase
        require(phase == Phase.Reg, "This function is not callable at this phase.");
        // add key
        p_keys.push(pk);
        registered++;
    }

    function register_client(address client_address, bytes memory pk) external {
        // only the operator can add new clients
        require(msg.sender == operator, "Only the operator can call this.");
        // check if we are at the registration phase
        require(phase == Phase.Reg, "This function is not callable at this phase.");
        // check if client already assigned a public key
        require(us_pk[client_address].length == 0, "Client already registered.");
        // add client
        us_pk[client_address] = pk;
    }

    // time: time for clients to send their hashed orders
    //       (this is basicly the trading duration)
    function trading_phase(uint time) external {
        // only the operator can initiate the trading phase
        require(msg.sender == operator, "Only the operator can call this.");
         // check if we are at the registration phase
        require(phase == Phase.Reg, "This function is not callable at this phase.");
        // change to trading phase
        phase = Phase.Trd;
        // set expiration time for trading day
        // trading time in blocks, 1 block is mined every ~12 seconds
        expiration = block.number + time;
        // emit event
        emit startPhase(Phase.Trd, expiration);
    }

    // time: time for clients to "reveal" their orders,
    //       otherwise orders are deemed invalid
    function reveal_phase(uint time) external {
        // only the operator can initiate the reveal phase
        require(msg.sender == operator, "Only the operator can call this.");
         // check if we are at the trading phase
        require(phase == Phase.Trd, "This function is not callable at this phase.");
        // check if we are at or past expiration
        require(block.number >= expiration, "Please wait for the expiration of the previous phase.");
        // change to reveal phase
        phase = Phase.Rev;
        // set expiration time
        expiration = block.number + time;
        // emit event
        emit startPhase(Phase.Rev, expiration);
    }

    function calc_phase() external {
        // only the operator can initiate the calculation phase
        require(msg.sender == operator, "Only the operator can call this.");
         // check if we are at the reveal phase
        require(phase == Phase.Rev, "This function is not callable at this phase.");
        // check if we are at or past expiration
        require(block.number >= expiration, "Please wait for the expiration of the previous phase.");
        // change to calculation phase
        phase = Phase.Cal;
        // emit event
        emit startPhase(Phase.Cal, 0);
    }

    function reveal_match(address buyer, bytes memory skB, string memory nameB, address seller,
                          bytes memory skS, string memory nameS, uint amount, uint price) external {
        // only the operator can reveal a match
        require(msg.sender == operator, "Only the operator can call this.");
         // check if we are at the calculation phase
        require(phase == Phase.Cal, "This function is not callable at this phase.");
        // check that two different clients were provided
        require(buyer != seller, "Buyer and Seller must not be the same.");
        // check if buyer has provided all details
        // check if commitment exists
        require(orders[buyer]._commitment.length > 0, "No commitment provided by this buyer.");
        // check if ciphertext exists
        require(orders[buyer]._ciphertext.length > 0, "No ciphertext provided by this buyer.");
        // publish secret key, allowing verification
        orders[buyer]._sk = skB;
        // check if seller has provided all details
        // check if commitment exists
        require(orders[seller]._commitment.length > 0, "No commitment provided by this buyer.");
        // check if ciphertext exists
        require(orders[seller]._ciphertext.length > 0, "No ciphertext provided by this buyer.");
        // publish secret key, allowing verification
        orders[seller]._sk = skS;
        // emit events
        emit secretRevealed(buyer, orders[buyer]._commitment, orders[buyer]._ciphertext, skB);
        emit secretRevealed(seller, orders[seller]._commitment, orders[seller]._ciphertext, skS);
        emit logTrade(nameB, nameS, amount, price);
    }

    // time: time for clients to check if their order was executed, validate
    //       the algorithm and send new address for the next trading day
    function res_phase(uint time) external {
        // only the operator can initiate the results phase
        require(msg.sender == operator, "Only the operator can call this.");
         // check if we are at the calculation phase
        require(phase == Phase.Cal, "This function is not callable at this phase.");
        // change to results phase
        phase = Phase.Res;
        // set expiration time
        expiration = block.number + time;
        // emit event
        emit startPhase(Phase.Res, expiration);
    }

    function reg_phase() external {
        // only the operator can initiate the registration phase
        require(msg.sender == operator, "Only the operator can call this.");
         // check if we are at the results phase
        require(phase == Phase.Res, "This function is not callable at this phase.");
        // check if we are at or past expiration
        require(block.number >= expiration, "Please wait for the expiration of the previous phase.");
        // change to the registration phase
        phase = Phase.Reg;
        if (mode > 3) {
            // delete all public keys, set variables to zero
            delete p_keys;
            registered = 0;
            used = 0;
        }
        // emit event
        emit startPhase(Phase.Reg, 0);
    }

    // *** IMPORTANT NOTE: ***
    // After calling reg_phase (so after the end of a trading day) the operator MUST
    // delete and reregister(in random order) every client that took part in the previous
    // trading day, otherwise their previous order won't be deleted from the smart contract
    // (this could lead to previous orders re-executing)

    function remove_client(address client_address) external {
        // only the operator can add new clients
        require(msg.sender == operator, "Only the operator can call this.");
        // check if we are at the registration phase
        require(phase == Phase.Reg, "This function is not callable at this phase.");
        // check if client already assigned a public key
        require(us_pk[client_address].length != 0, "Client not registered.");
        // remove old order if any
        delete orders[client_address];
        // delete clients public key
        delete us_pk[client_address];
    }

    // *** Client functions ***

    function register_key() external {
        // check if we are at the trading phase
        require(phase == Phase.Trd, "This function is not callable at this phase.");
        // an address can only register once
        require(us_pk[msg.sender].length == 0, "Address is already registered.");
        // chceck if there are available public keys
        require(used <= registered, "No spaces left.");
        // claim public key
        us_pk[msg.sender] = p_keys[used];
        used++;
    }

    function commit_order(bytes memory hashed_order) external {
         // check if we are at the trading phase
        require(phase == Phase.Trd, "This function is not callable at this phase.");
        // only a registered user can commit an order
        require(us_pk[msg.sender].length > 0, "Address does not correspond to a registered user.");
        // add commitment only (nonce and ciphertext set to default values)
        orders[msg.sender]._commitment = hashed_order;
    }

    function cancel_order() external {
         // check if we are at the trading phase
        require(phase == Phase.Trd, "This function is not callable at this phase.");
        // only a registered user can cancel an order
        require(us_pk[msg.sender].length > 0, "Transaction address does not correspond to a registered user.");
        // check if client has commited to an order
        require(orders[msg.sender]._commitment.length > 0, "No commitment was made.");
        // delete commitment
        delete(orders[msg.sender]._commitment);
    }

    function change_order(bytes memory hashed_order) external {
         // check if we are at the trading phase
        require(phase == Phase.Trd, "This function is not callable at this phase.");
        // only a registered user can change an order
        require(us_pk[msg.sender].length > 0, "Transaction address does not correspond to a registered user.");
        // check if client has commited to an order
        require(orders[msg.sender]._commitment.length > 0, "No commitment was made.");
        // change the commitment
        orders[msg.sender]._commitment = hashed_order;
    }

    function reveal_order(bytes memory ciphertext) external {
        // check if we are at the reveal phase
        require(phase == Phase.Rev, "This function is not callable at this phase.");
        // only a registered user can commit an order
        require(us_pk[msg.sender].length > 0, "Transaction address doesn't correspond to a registered user.");
        // check if commitment exists
        require(orders[msg.sender]._commitment.length > 0, "No commitment was made.");
        // add nonce and ciphertext
        orders[msg.sender]._ciphertext = ciphertext;
        // emit event
        emit commitmentRevealed(msg.sender, orders[msg.sender]._commitment, orders[msg.sender]._ciphertext);
    }
}
