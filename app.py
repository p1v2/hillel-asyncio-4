import asyncio
import random
from asyncio import sleep as async_sleep, Lock, Queue, Semaphore


class Pizza:
    TYPES = {
        'Margherita': {'prep_time': 2, 'bake_time': 3, 'pack_time': 1},
        'Pepperoni': {'prep_time': 3, 'bake_time': 4, 'pack_time': 2},
        'Veggie': {'prep_time': 2, 'bake_time': 2, 'pack_time': 1}
    }
    PRIORITIES = ['Normal', 'Urgent']

    def __init__(self, pizza, type=None, priority='Normal'):
        self.pizza = pizza
        self.type = type if type else random.choice(list(Pizza.TYPES.keys()))
        self.priority = priority
        self.status = 'in_fridge'

    def get_times(self):
        return Pizza.TYPES[self.type]

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

    async def make_busy(self, seconds, pizza):
        await self.lock.acquire()
        self.active_pizza = pizza
        await async_sleep(seconds)
        self.lock.release()

    async def get_ingredients_from_fridge(self, pizza):
        await self.make_busy(1, pizza)
        pizza.status = 'to_make'
        await make_queue.put(pizza)

    async def make_pizza(self, pizza):
        await self.make_busy(pizza.get_times()['prep_time'], pizza)
        pizza.status = 'made'
        await put_into_oven_queue.put(pizza)

    async def put_into_oven(self, pizza, ovens_semaphore):
        await ovens_semaphore.acquire()
        await self.make_busy(1, pizza)
        pizza.status = 'in_oven'
        await oven_queue.put(pizza)

    async def take_out_of_oven(self, pizza, ovens_semaphore):
        await self.make_busy(pizza.get_times()['bake_time'], pizza)
        ovens_semaphore.release()
        pizza.status = 'to_pack'
        await pack_queue.put(pizza)

    async def pack_pizza(self, pizza):
        await self.make_busy(pizza.get_times()['pack_time'], pizza)
        pizza.status = 'to_deliver'
        await deliver_queue.put(pizza)

    async def deliver_pizza(self, pizza):
        await self.make_busy(1, pizza)
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
                await self.make_pizza(pizza)
            elif not fridge_queue.empty():
                pizza = await fridge_queue.get()
                await self.get_ingredients_from_fridge(pizza)
            else:
                self.active_pizza = None
                await async_sleep(1)


class PizzaSpecialist(PizzaMaker):
    def __init__(self, number, specialties):
        super().__init__(number)
        self.specialties = specialties

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
                if pizza.type in self.specialties:
                    await self.make_pizza(pizza)
                else:
                    await make_queue.put(pizza)  # Put it back if not specialized
            elif not fridge_queue.empty():
                pizza = await fridge_queue.get()
                if pizza.type in self.specialties:
                    await self.get_ingredients_from_fridge(pizza)
                else:
                    await fridge_queue.put(pizza)  # Put it back if not specialized
            else:
                self.active_pizza = None
                await async_sleep(1)


class Oven:
    def __init__(self):
        self.lock = Lock()

    async def do_the_job(self):
        while True:
            if not oven_queue.empty():
                pizza = await oven_queue.get()
                await async_sleep(4)  # Fixed baking time in the oven
                pizza.status = 'baked'
                await take_out_of_oven_queue.put(pizza)
            else:
                await async_sleep(0.1)


# Queues for each stage of the pizza process
fridge_queue = Queue()
make_queue = Queue()
put_into_oven_queue = Queue()
take_out_of_oven_queue = Queue()
pack_queue = Queue()
deliver_queue = Queue()
oven_queue = Queue()


async def console_job(pizzas, workers):
    while True:
        print('\033[H\033[J')  # Clear console
        for pizza in pizzas:
            active_worker = next((worker for worker in workers if worker.active_pizza == pizza), None)
            status_order = Pizza.STATUSES.index(pizza.status)
            print(f'Pizza {pizza.pizza} ({pizza.type}, {pizza.priority}): {"*" * status_order}{"-" * (len(Pizza.STATUSES) - status_order - 1)}', end='')
            if active_worker:
                specialist_info = f' (Specialist in: {", ".join(active_worker.specialties)})' if isinstance(active_worker, PizzaSpecialist) else ''
                print(f' ({active_worker.number}{specialist_info})', end='')
            print()
        print()
        await async_sleep(1)


async def main():
    print("Welcome to the pizza factory!")
    workers_amount = int(input('Enter the amount of workers: '))
    pizza_amount = int(input('Enter the amount of pizzas: '))
    ovens_amount = int(input('Enter the amount of ovens: '))

    ovens = [Oven() for _ in range(ovens_amount)]
    ovens_semaphore = Semaphore(ovens_amount)

    # Assign workers as either specialists or regular pizza makers
    workers = []
    for i in range(workers_amount):
        if i % 2 == 0:
            workers.append(PizzaSpecialist(i + 1, specialties=random.sample(list(Pizza.TYPES.keys()), 2)))
        else:
            workers.append(PizzaMaker(i + 1))

    worker_tasks = [asyncio.create_task(worker.do_the_job(ovens_semaphore)) for worker in workers]
    oven_tasks = [asyncio.create_task(oven.do_the_job()) for oven in ovens]

    # Create pizzas with random priorities
    pizzas = [Pizza(i + 1, priority=random.choice(Pizza.PRIORITIES)) for i in range(pizza_amount)]
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

    # Cancel all tasks after completion
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
