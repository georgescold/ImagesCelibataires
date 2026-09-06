# -*- coding: utf-8 -*-
"""
Banque de LIEUX (fonds concrets), separee des types de scene.

Contrainte : un fond utilise pour une femme ne doit pas revenir avant
30 generations de femmes. A 5 photos par femme, cela bloque 150 fonds
en permanence -> il en faut nettement plus de 150 au total.

15 types de scene x 15 fonds concrets = 225 fonds distincts.
Un registre (gen/_lieux_utilises.json) memorise le numero de generation
de chaque fond et applique le delai de carence.
"""
import json, os, random

REGISTRE = "gen/_lieux_utilises.json"
CARENCE = 30

LIEUX = {

"salon": [
 "in her living room, a beige fabric sofa, a radiator under the window and a folded throw",
 "in her living room, a dark green velvet sofa, a brass floor lamp and a stack of magazines",
 "in her living room, a worn brown leather sofa, a low pine table and a rug with a turned-up corner",
 "in her living room, a grey corner sofa, a wall of framed photos and a games console on the floor",
 "in her living room, a small flat with a sofa bed, a clothes rail and a bare bulb",
 "in her living room, floral wallpaper, a mantelpiece with ornaments and a gas fire",
 "in her living room, white walls, a low bookcase and a large dying pot plant",
 "in her living room, a blue two-seater, net curtains and a cat tree in the corner",
 "in her living room, a converted attic with a sloping ceiling and a skylight",
 "in her living room, a cream sofa, patio doors onto a small yard and a drying rack",
 "in her living room, dark wood panelling, a heavy sideboard and a ticking clock",
 "in her living room, an open-plan flat with a kitchen counter behind the sofa",
 "in her living room, a mustard armchair, exposed brick and a bike against the wall",
 "in her living room, a chintz sofa with a crocheted blanket and a display cabinet",
 "in her living room, a rented flat with bare magnolia walls and a single lamp",
],

"cuisine": [
 "in her kitchen, white units, a kettle, a draining rack and a fridge covered in magnets",
 "in her kitchen, dated oak units, a gas hob and a strip light under the cupboards",
 "in her kitchen, a narrow galley with a washing machine and drying laundry above",
 "in her kitchen, green tiles, a butler sink and a window over the garden",
 "in her kitchen, a small breakfast bar with two stools and a fruit bowl",
 "in her kitchen, red units, a microwave on the counter and a wall calendar with no writing",
 "in her kitchen, a rustic farmhouse room with a wooden table and a range cooker",
 "in her kitchen, grey gloss units, a chrome tap and a knife block",
 "in her kitchen, a cramped studio kitchenette with a two-ring hob",
 "in her kitchen, cream units, a tiled splashback and a clothes horse in the corner",
 "in her kitchen, a black and white checked floor and open shelving with jars",
 "in her kitchen, pine units, a bread bin and a radio on the windowsill",
 "in her kitchen, a modern flat with an island and pendant lights",
 "in her kitchen, an older room with lino, a chest freezer and a back door ajar",
 "in her kitchen, blue units, a dishwasher standing open and a pile of post on the side",
],

"salle_de_bain": [
 "in a bathroom with white tiles, a towel on the radiator and toothbrushes in a glass",
 "in a bathroom with beige tiles, a shower curtain and a mirrored cabinet",
 "in a bathroom with a green suite from the eighties and a pedestal basin",
 "in a bathroom with grey tiles, a heated towel rail and a bath panel",
 "in a small windowless bathroom with an extractor fan and a strip light",
 "in a bathroom with pink tiles, a laundry basket and a bath mat rucked up",
 "in a bathroom with white subway tiles, a wooden stool and plants on the sill",
 "in a bathroom with a corner shower, a mirror fogged at the edges and a razor on the sill",
 "in a bathroom with black floor tiles, a large round mirror and a hanging towel",
 "in a bathroom with a claw-foot bath, patterned floor tiles and a wicker basket",
 "in a bathroom with a mirror over a cluttered vanity unit full of bottles",
 "in a bathroom with cream tiles, a scale on the floor and a dressing gown on the door",
 "in a bathroom with a skylight, white walls and a wooden ladder rail",
 "in a rented bathroom with mismatched fittings and a chipped basin",
 "in a bathroom with a mirrored wall, a downlight and a folded hand towel",
],

"chambre": [
 "in her bedroom, an unmade bed, a wardrobe door ajar and a chair piled with clothes",
 "in her bedroom, a made bed with a floral duvet, a dressing table and a jewellery dish",
 "in her bedroom, a small room with a single wardrobe and a full-length mirror on the door",
 "in her bedroom, grey walls, a bedside lamp and a phone charger trailing across the bed",
 "in her bedroom, an attic room with a sloping ceiling and a suitcase in the corner",
 "in her bedroom, a bed under a window, radiator below and curtains half drawn",
 "in her bedroom, mirrored wardrobe doors and a laundry pile at the foot of the bed",
 "in her bedroom, white walls, a rattan headboard and fairy lights not switched on",
 "in her bedroom, a heavy dark wardrobe, a rug and a bedside pile of books",
 "in her bedroom, a small flat where the bed is against the wall and a rail holds her clothes",
 "in her bedroom, blue walls, a chest of drawers and a mirror leaning against it",
 "in her bedroom, a double bed with a knitted throw and a cat asleep on the corner",
 "in her bedroom, a spare room with boxes stacked along one wall",
 "in her bedroom, a bright room with a wicker chair and an open window",
 "in her bedroom, beige walls, a mirrored dressing table and a hairdryer left out",
],

"voiture": [
 "in a small hatchback parked in a supermarket car park, trolleys visible through the glass",
 "in an old estate car parked on a residential street, hedges through the windscreen",
 "in a compact car parked in a multi-storey, concrete pillars and strip lights behind",
 "in a car parked at a motorway service area, lorries in the background",
 "in a car parked on a gravel drive in front of a house",
 "in a small city car parked at the kerb, a bus stop behind",
 "in a car parked by a beach car park, dunes and grey sea through the window",
 "in a work van parked outside a depot, a clipboard on the dashboard",
 "in a car parked under trees, dappled light on the windscreen",
 "in a car at a petrol station, the pump and canopy visible behind",
 "in a car parked outside a school gate, railings behind",
 "in a car in a hospital car park, a low brick building behind",
 "in a car parked on a country lane, a hedge pressed against the door",
 "in a car parked at a retail park, big flat units in the distance",
 "in a car parked in a garage with the door open onto the drive",
],

"salle_de_sport": [
 "in a small gym, a dumbbell rack, a bench and a strip light overhead",
 "in a basement gym, low ceiling, rubber flooring and a squat rack",
 "in a hotel gym, two treadmills, a mirror wall and a water cooler",
 "in a municipal sports hall converted to a weights room, high windows",
 "in a converted garage gym at home, a single bench and mismatched weights",
 "in a busy chain gym, rows of machines receding behind her",
 "in a small studio with mats rolled against the wall and a wall mirror",
 "in a gym changing room with lockers and a bench",
 "in a gym corridor with a mirror and a noticeboard with nothing written on it",
 "in a gym stretching area with foam rollers and a mirrored wall",
 "in an old-fashioned gym with wooden floor and cast iron weights",
 "in a bright gym with floor-to-ceiling windows onto a car park",
 "in a compact gym under a block of flats, pipes across the ceiling",
 "in a gym with red rubber flooring and a boxing bag in the corner",
 "in a quiet gym at an off-peak hour, most machines empty behind her",
],

"terrasse_cafe": [
 "on a cafe terrace with metal chairs, a hedge and part of a parked car behind",
 "on a cafe terrace under a canvas awning, a cobbled street behind",
 "on a cafe terrace beside a square with a fountain out of focus",
 "on a cafe terrace on a wide boulevard, plane trees along the pavement",
 "on a cafe terrace by a harbour, masts and rigging behind",
 "on a small terrace outside a bakery with two tables on the pavement",
 "on a cafe terrace in a pedestrian street with people walking past",
 "on a terrace overlooking a river with a stone bridge behind",
 "on a cafe terrace with wicker chairs and heaters not switched on",
 "on a terrace at a motorway stop with a car park behind",
 "on a cafe terrace in a market square with empty stalls behind",
 "on a rooftop terrace with a low wall and rooftops beyond",
 "on a cafe terrace beside a park railing, trees behind",
 "on a garden centre cafe terrace with plants on shelves behind",
 "on a beachfront cafe terrace with a wooden deck and grey sea behind",
],

"rue": [
 "on the pavement of a residential street, hedges, a driveway and parked cars",
 "on a suburban street of pebbledash houses with wheelie bins out",
 "on a narrow street of terraced houses with cars nose to tail",
 "on a village street with shuttered stone houses",
 "outside a block of flats with a low wall and a bike rack",
 "on a wide street with plane trees and a bus lane",
 "on a quiet cul-de-sac with a turning circle and a lamp post",
 "on a street of new-build houses with young trees in the verge",
 "outside a row of small shops with awnings and no readable signs",
 "on a steep street with steps up one side and railings",
 "on a street beside a park railing with leaves on the pavement",
 "on a pavement beside roadworks with barriers and cones",
 "outside a train station entrance with a taxi rank behind",
 "on a market street on a quiet day, empty stall frames behind",
 "on a street corner with a postbox and a pelican crossing",
],

"parc": [
 "in a park with grass, trees, a bench and a bin",
 "in a park with a duck pond and railings",
 "in a formal park with gravel paths and clipped hedges",
 "in a park with a bandstand out of focus behind",
 "in a small urban square with a few trees and benches",
 "in a park with a children's play area behind, empty",
 "in a park in autumn with leaves thick on the grass",
 "in a park with a long avenue of trees receding behind her",
 "on a common with rough grass and a distant treeline",
 "in a park with a war memorial and low chains around it",
 "in a park beside a tennis court with a chain-link fence",
 "in a park with a rose garden and a gravel path",
 "in a park on a slope with the town visible below",
 "in a park with a cafe kiosk shuttered behind",
 "in a park beside a canal with a towpath",
],

"balcon": [
 "on a narrow balcony with a drying rack, a plastic chair and rooftops below",
 "on a balcony with a wrought iron railing and window boxes",
 "on a balcony with a glass balustrade overlooking a car park",
 "on a small Juliet balcony with the window pushed open",
 "on a balcony with a bistro table for two and a folded parasol",
 "on a balcony overlooking a courtyard with washing lines opposite",
 "on a top-floor balcony with a view over slate roofs",
 "on a balcony with a bike leaning against the wall and a mop",
 "on a balcony overlooking a busy road with trees along it",
 "on a balcony with tomato plants in pots and a watering can",
 "on a concrete balcony of a tower block with a hazy skyline",
 "on a balcony facing another building a few metres away",
 "on a balcony with a rattan sofa and a cushion left out in the rain",
 "on a balcony with a sea view in the far distance between buildings",
 "on a shaded balcony with a blind half lowered",
],

"vacances": [
 "on a seafront promenade with palms, scooters and a beach bar",
 "in an old village street with stone walls and shuttered windows",
 "on a harbour quay with fishing boats and coiled rope",
 "on a wide sandy beach with a grey sky and a breakwater",
 "on a hilltop viewpoint with a valley behind",
 "in a market square abroad with awnings and crates",
 "on a coastal path with cliffs and gorse",
 "beside a lake with wooded hills behind",
 "in a narrow alley with steps and hanging plants",
 "on a stone jetty with the sea on both sides",
 "in front of an old church door in a small town",
 "on a promenade with a Ferris wheel out of focus behind",
 "in a pine forest campsite with tents behind",
 "on a mountain road with a guardrail and a drop behind",
 "at a ferry terminal with a gangway and railings behind",
],

"soiree": [
 "at a restaurant table at night, dark walls and a blurred shoulder beside her",
 "at a long table in a busy bistro with glasses and plates",
 "in a dim bar with bottles out of focus behind",
 "at a table outside at night under a string of lights",
 "in a function room with a paper tablecloth and folding chairs",
 "in a pizzeria with red banquettes and a dark window",
 "at a kitchen table at a friend's house with the remains of a meal",
 "in a small wine bar with barrels along the wall",
 "at a table in a brasserie with mirrors and dark wood",
 "in a crowded pub with people out of focus behind",
 "at a table on a covered terrace at night with heaters",
 "in a modern restaurant with concrete walls and low lighting",
 "at a family table with a patterned tablecloth and a cake",
 "in a bar with a pool table out of focus behind",
 "at a table by a window at night with reflections in the glass",
],

"jardin": [
 "in a small back garden with a fence, a lawn and a folded parasol",
 "in a garden with a shed, a water butt and a wheelbarrow",
 "on a paved patio with pots and a bistro set",
 "in a garden with a washing line and a trampoline behind",
 "in a long narrow garden with a path down the middle",
 "in a garden with raised vegetable beds and canes",
 "in a courtyard garden with high walls and climbing plants",
 "in a garden with a low brick wall and a view of fields",
 "on a decked area with steps down to a lawn",
 "in a garden with an apple tree and windfalls on the grass",
 "in a front garden with a gate and a gravel path",
 "in a garden with a greenhouse and a compost bin",
 "on a small terrace with artificial grass and a parasol base",
 "in a garden in winter with bare shrubs and a covered barbecue",
 "in an allotment with a shed and rows of vegetables",
],

"travail": [
 "in an office with a plain wall, a desk edge and flat overhead light",
 "in a stockroom with metal shelving and cardboard boxes",
 "in a staff room with a kettle, a noticeboard and mismatched chairs",
 "behind the counter of a small shop with shelves behind",
 "in a salon with a mirror station and a chair",
 "in a clinic corridor with a plain wall and a hand gel dispenser",
 "in a school classroom with a whiteboard wiped clean",
 "in a warehouse aisle with pallets and racking",
 "in a small workshop with a bench and tools on a board",
 "in an open-plan office with dividers and monitors behind",
 "in a hotel reception area with a plain desk",
 "in a bakery kitchen with steel surfaces and trays",
 "in a garden centre aisle with plants on trolleys",
 "in a nursery playroom with low furniture and soft mats",
 "in a laboratory corridor with plain doors and a fire extinguisher",
],

"animal": [
 "at home with a scruffy terrier, a cluttered living room behind",
 "at home with a tabby cat, a kitchen counter behind",
 "at home with a black labrador, a hallway with coats on hooks",
 "at home with a ginger cat, a bedroom with an unmade bed behind",
 "at home with a spaniel, a utility room with a washing machine",
 "at home with a white cat, a sofa and a bookshelf behind",
 "at home with an old dog on a blanket, a dim living room",
 "at home with a kitten, a cluttered dining table behind",
 "at home with a greyhound on a sofa, a plain wall behind",
 "at home with two cats, a stair landing behind",
 "at home with a small dog on her lap, a conservatory behind",
 "at home with a cat on a windowsill, net curtains behind",
 "at home with a wet dog after a walk, a back door and boots",
 "at home with a dog in a hallway, a mirror and a radiator",
 "at home with a cat on a bed, a wardrobe behind",
],
}


def charger():
    if os.path.exists(REGISTRE):
        d = json.load(open(REGISTRE, encoding='utf-8'))
        return d.get("gen", 0), d.get("lieux", {})
    return 0, {}


def sauver(gen, registre):
    json.dump({"gen": gen, "lieux": registre}, open(REGISTRE, 'w', encoding='utf-8'), indent=0)


def choisir(scene, gen, registre, rnd):
    """Un lieu de cette scene non utilise depuis au moins CARENCE generations."""
    pool = LIEUX[scene]
    libres = [x for x in pool if gen - registre.get(x, -10 ** 9) >= CARENCE]
    if libres:
        return rnd.choice(libres), True
    # banque epuisee pour ce type de scene : on prend le moins recemment utilise
    return min(pool, key=lambda x: registre.get(x, -10 ** 9)), False


def dispo(scene, gen, registre):
    """Nombre de lieux encore utilisables pour ce type de scene."""
    return sum(1 for x in LIEUX[scene] if gen - registre.get(x, -10 ** 9) >= CARENCE)


def scenes_disponibles(n, gen, registre, rnd):
    """Tire n types de scene en privilegiant ceux dont la banque de lieux est la plus libre.
    Evite qu'un type s'epuise et force une repetition de fond."""
    cand = sorted(LIEUX, key=lambda sc: (-dispo(sc, gen, registre), rnd.random()))
    # on garde un vivier large (les 10 plus libres) puis on tire dedans au hasard
    vivier = [sc for sc in cand if dispo(sc, gen, registre) > 0][:10] or cand[:n]
    rnd.shuffle(vivier)
    return vivier[:n]


if __name__ == "__main__":
    total = sum(len(v) for v in LIEUX.values())
    print(f"{len(LIEUX)} types de scene, {total} lieux distincts")
    print(f"carence = {CARENCE} generations -> {CARENCE * 5} lieux bloques au maximum")
    print("marge :", total - CARENCE * 5, "lieux toujours disponibles")
    # simulation : 60 femmes, on verifie qu'aucun lieu ne revient trop tot
    rnd = random.Random(0)
    reg, dernier, viol = {}, {}, 0
    for g in range(60):
        for sc in scenes_disponibles(5, g, reg, rnd):
            lieu, ok = choisir(sc, g, reg, rnd)
            if lieu in dernier and g - dernier[lieu] < CARENCE:
                viol += 1
            dernier[lieu] = g
            reg[lieu] = g
    print(f"simulation 60 femmes (300 photos) -> violations de carence : {viol}")
