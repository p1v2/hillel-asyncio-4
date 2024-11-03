import asyncio
import random

from asyncio import sleep as async_sleep, Lock, Queue, Semaphore


class PriorityQueue:
    def __init__(self):
        self.urgent_queue = Queue()
        self.normal_queue = Queue()

    async def put(self, pizza):
        if pizza.priority == "Urgent":
            await self.urgent_queue.put(pizza)
        else:
            await self.normal_queue.put(pizza)

    async def get(self):
        if not self.urgent_queue.empty():
            return await self.urgent_queue.get()
        return await self.normal_queue.get()

    def empty(self):
        return self.urgent_queue.empty() and self.normal_queue.empty()

    async def join(self):
        await self.urgent_queue.join()
        await self.normal_queue.join()


class Pizza:
    def __init__(self, pizza, pizza_type, priority="Normal"):
        self.pizza = pizza
        self.type = pizza_type
        self.priority = priority
        self.status = 'in_fridge'

    TYPES_OF_PIZZAS = {
        'Margherita': {'make': 3, 'bake': 3, 'pack': 1},
        'Pepperoni': {'make': 2, 'bake': 4, 'pack': 2},
        'Veggie': {'make': 6, 'bake': 3.5, 'pack': 1.5},
        'Hawaiian': {'make': 5, 'bake': 3, 'pack': 1},
        'BBQ Chicken': {'make': 3, 'bake': 4.5, 'pack': 2.5},
        'Meat Lovers': {'make': 2, 'bake': 5, 'pack': 2},
        'Supreme': {'make': 6, 'bake': 4.5, 'pack': 2},
        'Four Cheese': {'make': 10, 'bake': 3.5, 'pack': 1},
        'Buffalo Chicken': {'make': 3, 'bake': 4, 'pack': 1.5},
        'Mushroom': {'make': 2, 'bake': 3, 'pack': 1},
        'Truffle': {'make': 8, 'bake': 5, 'pack': 2},
        'Seafood': {'make': 14, 'bake': 5.5, 'pack': 2.5},
        'Pesto': {'make': 3, 'bake': 3.5, 'pack': 1.5},
        'White Pizza': {'make': 8, 'bake': 4, 'pack': 1.5},
        'Mexican': {'make': 6, 'bake': 4.5, 'pack': 2},
        'Calzone': {'make': 5, 'bake': 4.5, 'pack': 2}
    }

    STATUSES = (
        'in_fridge',
        'to_make',
        'made',
        'in_oven',
        'baked',
        'to_pack',
        'to_deliver',
        'delivered'
    )


class PizzaMaker:
    def __init__(self, number):
        self.lock = Lock()
        self.active_pizza = None
        self.number = number

    async def make_busy(self, stage, pizza):
        seconds = Pizza.TYPES_OF_PIZZAS[pizza.type][stage]
        await self.lock.acquire()
        self.active_pizza = pizza
        await async_sleep(seconds)
        self.lock.release()

    def can_make(self, pizza):
        return True

    async def get_ingredients_from_fridge(self, pizza):
        await self.make_busy('make', pizza)
        pizza.status = 'to_make'
        await make_queue.put(pizza)

    async def make_pizza(self, pizza):
        await self.make_busy('make', pizza)
        pizza.status = 'made'
        await put_into_oven_queue.put(pizza)

    async def put_into_oven(self, pizza, ovens_semaphore):
        await ovens_semaphore.acquire()
        await self.make_busy('bake', pizza)
        pizza.status = 'in_oven'
        await oven_queue.put(pizza)

    async def take_out_of_oven(self, pizza, ovens_semaphore):
        await self.make_busy('bake', pizza)
        ovens_semaphore.release()
        pizza.status = 'to_pack'
        await pack_queue.put(pizza)

    async def pack_pizza(self, pizza):
        await self.make_busy('pack', pizza)
        pizza.status = 'to_deliver'
        await deliver_queue.put(pizza)

    async def deliver_pizza(self, pizza):
        await self.make_busy('pack', pizza)
        pizza.status = 'delivered'

    async def do_the_job(self, ovens_semaphore):
        while True:
            if not deliver_queue.empty():
                pizza = await deliver_queue.get()
                await self.deliver_pizza(pizza)
            elif not pack_queue.empty():
                pizza = await pack_queue.get()
                await self.pack_pizza(pizza)
            elif not take_out_of_oven_queue.empty():
                pizza = await take_out_of_oven_queue.get()
                await self.take_out_of_oven(pizza, ovens_semaphore)
            elif not put_into_oven_queue.empty() and not ovens_semaphore.locked():
                pizza = await put_into_oven_queue.get()
                await self.put_into_oven(pizza, ovens_semaphore)
            elif not make_queue.empty():
                pizza = await make_queue.get()
                if not self.can_make(pizza):
                    await make_queue.put(pizza)
                    await async_sleep(0.1)
                    continue
                await self.make_pizza(pizza)
            elif not fridge_queue.empty():
                pizza = await fridge_queue.get()
                if not self.can_make(pizza):
                    await fridge_queue.put(pizza)
                    await async_sleep(0.1)
                    continue
                await self.get_ingredients_from_fridge(pizza)
            else:
                self.active_pizza = None
                await async_sleep(1)


class PizzaSpecialist(PizzaMaker):
    def __init__(self, number, specialties):
        super().__init__(number)
        self.specialties = specialties

    def can_make(self, pizza):
        return pizza.type in self.specialties


class Oven:
    def __init__(self):
        self.lock = Lock()

    async def do_the_job(self):
        while True:
            if not oven_queue.empty():
                pizza = await oven_queue.get()
                await async_sleep(4)
                pizza.status = 'baked'
                await take_out_of_oven_queue.put(pizza)
            else:
                await async_sleep(0.1)


fridge_queue = PriorityQueue()
make_queue = PriorityQueue()
put_into_oven_queue = PriorityQueue()
take_out_of_oven_queue = PriorityQueue()
pack_queue = PriorityQueue()
deliver_queue = PriorityQueue()

oven_queue = PriorityQueue()


async def console_job(pizzas, workers):
    while True:
        # Clear the console
        print('\033[H\033[J')
        for pizza in pizzas:
            active_worker = next((worker for worker in workers if worker.active_pizza == pizza), None)
            status_order = Pizza.STATUSES.index(pizza.status)

            print(
                f'Pizza {pizza.pizza} ({pizza.type}, {pizza.priority}): {"*" * status_order}{"-" * (len(Pizza.STATUSES) - status_order - 1)}',
                end='')
            print(f' ({pizza.status})', end='')
            if active_worker:
                if isinstance(active_worker, PizzaSpecialist):
                    specialties = ', '.join(active_worker.specialties)
                    print(f' (Worker {active_worker.number} - Specialist: {specialties})', end='')
                else:
                    print(f' (Worker {active_worker.number})', end='')
            print()
        print()
        await async_sleep(1)


async def main():
    print("Welcome to the pizza factory!")
    workers_amount = int(input('Enter the amount of workers: '))
    pizza_amount = int(input('Enter the amount of pizzas: '))
    ovens_amount = int(input('Enter the amount of ovens: '))
    pizza_types = list(Pizza.TYPES_OF_PIZZAS.keys())

    if workers_amount > 1:
        specialists_amount = random.randint(workers_amount // 3, workers_amount - 1)
    else:
        specialists_amount = 0

    workers = [PizzaMaker(i + 1) for i in range(workers_amount - specialists_amount)]

    for i in range(specialists_amount):
        specialties = random.sample(pizza_types, k=2)
        specialist = PizzaSpecialist(workers_amount - specialists_amount + i + 1, specialties)
        workers.append(specialist)

    ovens = [Oven() for _ in range(ovens_amount)]
    ovens_semaphore = Semaphore(ovens_amount)

    worker_tasks = [asyncio.create_task(worker.do_the_job(ovens_semaphore)) for worker in workers]
    oven_tasks = [asyncio.create_task(oven.do_the_job()) for oven in ovens]
    priority_levels = ["Normal", "Urgent"]
    pizzas = [Pizza(i + 1, random.choice(pizza_types), random.choice(priority_levels)) for i in range(pizza_amount)]

    fridge_tasks = [fridge_queue.put(pizza) for pizza in pizzas]

    console_task = asyncio.create_task(console_job(pizzas, workers))

    await asyncio.gather(*fridge_tasks)

    await make_queue.join()
    await fridge_queue.join()
    await put_into_oven_queue.join()
    await take_out_of_oven_queue.join()
    await oven_queue.join()
    await pack_queue.join()
    await deliver_queue.join()

    for worker_task in worker_tasks:
        worker_task.cancel()

    for oven_task in oven_tasks:
        oven_task.cancel()

    console_task.cancel()

    await asyncio.gather(*worker_tasks)
    await asyncio.gather(*oven_tasks)
    await console_task


if __name__ == '__main__':
    asyncio.run(main())
